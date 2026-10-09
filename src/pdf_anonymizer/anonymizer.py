import pymupdf
import unicodedata
import pytesseract
import re
from PIL import Image
from collections.abc import Callable

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

tabela_traducao = str.maketrans({"B":"8","O":"0","I":"1","L":"1"})

def abrir_arquivo(arquivo: str) -> pymupdf.Document:
    doc = pymupdf.open(arquivo)
    return doc

def normalizar(s: str) -> str:                                   # Lívia   lívia   Iívia   LÍVIA
    s = unicodedata.normalize("NFD", s)                          # Li´via  li´via  Ii´via  LI´VIA
    s = "".join(c for c in s if unicodedata.category(c) != "Mn") # Livia   livia   Iivia   LIVIA
    s = "".join(c for c in s.upper() if c.isalnum())             # LIVIA   LIVIA   IIVIA   LIVIA
    return s.translate(tabela_traducao)                          # 11V1A   11V1A   11V1A   11V1A

def palavras_nativas(page: pymupdf.Page) -> list[tuple[pymupdf.Rect, str]]:
    palavras = []
    raw = page.get_text("rawdict")

    for bloco in raw["blocks"]:
        for linha in bloco.get("lines", []):     # blocos de imagem não têm "lines"
            texto, rect = "", None

            for span in linha["spans"]:
                for ch in span["chars"]:
                    c = ch["c"]
                    # Letras/números continuam a palavra; acentos soltos (Mn) também
                    if c.isalnum() or (texto and unicodedata.category(c) == "Mn"):
                        texto += c
                        r = pymupdf.Rect(ch["bbox"])
                        rect = r if rect is None else rect | r
                    elif texto:                  # espaço/pontuação fecha a palavra
                        palavras.append((rect, texto))
                        texto, rect = "", None

            if texto:                            # palavra no fim da linha
                palavras.append((rect, texto))

    return palavras

def _coberto(r: pymupdf.Rect, rects_texto: list[pymupdf.Rect]) -> bool:
    #True se pelo menos metade do desenho estiver sobre uma palavra nativa.
    for rt in rects_texto:
        inter = r & rt
        if not inter.is_empty and inter.get_area() >= 0.5 * r.get_area():
            return True
    return False

def contar_glifos_vetoriais(page: pymupdf.Page, nativas: list[tuple[pymupdf.Rect, str]], altura_max: float = 40) -> int:
    rects_texto = [r for r, _ in nativas]
    glifos = 0

    for d in page.get_drawings():
        if d["type"] not in ("f", "fs"):                       # letra é preenchida
            continue
        if not any(item[0] == "c" for item in d["items"]):     # letra tem curvas
            continue

        r = d["rect"]
        if r.is_empty or r.height > altura_max:                # descarta formas grandes
            continue
        if _coberto(r, rects_texto):                           # já é texto nativo
            continue

        glifos += 1

    return glifos

def precisa_ocr(page: pymupdf.Page, nativas: list[tuple[pymupdf.Rect, str]], min_glifos: int = 30) -> bool:

    if not nativas:
        print("Página sem texto")
        return True

    if page.get_images() or page.get_image_info():
        print("Página com imagens")
        return True

    # Texto desenhado como vetores (ex.: PDFs gerados pelo iOS/Quartz)
    return contar_glifos_vetoriais(page, nativas) >= min_glifos
    #return False

def ocr_palavras(page: pymupdf.Page, dpi: int = 400, limite: int = 170, psm: int = 11, margem: float = 0.5,) -> list[tuple[pymupdf.Rect, str]]:
    pix = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY) # Retorna um pixmap em tons de cinza

    tabela = bytes(255 if i > limite else 0 for i in range(256)) # Transforma a list em bytes para ser usada na tradução de pixels
    """ 
    valores = []
    for i in range(256): # Lógica para criar tabela de tradução de pixels
        if i > limite:
            valores.append(255)
        else:
            valores.append(0)
    tabela = bytes(valores) # Transforma a list em bytes para ser usada na tradução de pixels

    """
    img = Image.frombytes("L", (pix.width, pix.height), pix.samples.translate(tabela))
    """
    Image.frombytes(mode, size, data) -> Image
    - "L" = escala de cinza com 1 byte, "RGB" = cores com 3 bytes
    - pix.samples = pixels da imagem, 1 byte por pixel
    - pix.samples.translate(tabela) = pixels da imagem, com a tabela de tradução aplicada -> 0 = preto, 255 = branco

    """
    dados = pytesseract.image_to_data(img, lang="por", config=f"--psm {psm}", output_type=pytesseract.Output.DICT)
    """
    - config=f"--psm 11" -> Page Segmentation Mode - Procura texto espalhado
    - output_type=pytesseract.Output.DICT -> Retorna um dicionário

    dados = {
        "level":  [1,   2,   [...], 5,       5],
        "left":   [0,   120, [...], 120,     410],
        "top":    [0,   300, [...], 300,     302],
        "width":  [3400,800, [...], 270,     510],
        "height": [4400,60,  [...], 58,      56],
        "conf":   [-1,  -1,  [...], 91.5,    88.2], <-- Confiança da detecção, de 0 a 100 (-1 = entrada estrutural: página, bloco, linha)
        "text":   ["",  "",  [...], "Nome:", "Fulano"],
    }

    """
    escala = pymupdf.Matrix(72 / dpi, 72 / dpi) * page.derotation_matrix
    """
    pixels -> dots = pixels * fator de conversão
    dot = 1/72 inch
    dpi = dots per inch = Pontos por polegada
    fator de conversão = 72 / dpi

    page.derotation_matrix -> Corrige a rotação da página, caso exista

    """
    palavras = []

    for texto, l, t, w, h in zip(dados["text"], dados["left"], dados["top"], dados["width"], dados["height"]):
        """
        zip() -> Combina os elementos de várias listas em cada iteração, retornando uma tupla com os elementos correspondentes.
        Faz o mesmo que:
        
        for i in range(len(dados["text"])):
            texto = dados["text"][i]
            l = dados["left"][i]
            t = dados["top"][i]
            ...
    
        """
        if not texto.strip():
            continue

        rect = pymupdf.Rect(l, t, l + w, t + h) * escala
        """
        pymupdf.Rect(x0, y0, x1, y1)
        - x0, y0 = coordenadas do canto superior esquerdo do retângulo
        - x1, y1 = coordenadas do canto inferior direito do retângulo
        """
        n = len(texto)
        folga = h * 72 / dpi * margem

        for m in re.finditer(r"\w+", texto):
            """
            re.finditer() -> Retorna um iterador com todas as ocorrências de uma expressão regular em uma string
             = qualquer caractere alfanumérico (letra ou número)
            + = um ou mais vezes
            
            caractere | C P F : 1 2 3 . 4 5 6  .  7  8  9  -  0  0
            iterador  | 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17
            match     | [tk1]   [tk2]   [tk3]     [ tk4 ]     [tk5]
            """  
            x0 = rect.x0 + rect.width * m.start() / n - folga
            x1 = rect.x0 + rect.width * m.end() / n + folga
            token = m.group() 
            
            palavras.append((pymupdf.Rect(x0, rect.y0, x1, rect.y1), token))

    return palavras

def buscar_termo(palavras: list[tuple[pymupdf.Rect, str]], termo: str) -> list[pymupdf.Rect]:
    alvo = "".join(normalizar(p) for p in re.findall(r"\w+", termo))
    textos = [normalizar(t) for _, t in palavras]  

    areas = []
    if not alvo:
        return areas

    for i in range(len(textos)):
        acumulado = ""
        for j in range(i, len(textos)):
            acumulado += textos[j]

            if acumulado == alvo:
                areas.extend(rect for rect, _ in palavras[i:j + 1])
                break

            if not alvo.startswith(acumulado):
                break
    return areas

def censurar_dados(doc: pymupdf.Document, termos: list[str], saida: str, log: Callable[[str], None] = print, ao_avancar: Callable[[int, int], None] | None = None) -> None:
    total = doc.page_count
    for page in doc:
        log(f"Página {page.number +1} de {total}")

        nativas = palavras_nativas(page)
        ocr = None

        if precisa_ocr(page, nativas):
            ocr = ocr_palavras(page)
            log("Página com texto não extraível (imagem ou vetores), aplicando OCR...")

        for termo in termos:
            areas = buscar_termo(nativas, termo)

            if ocr is not None:
                areas += buscar_termo(ocr, termo)
                
            if not areas:
                log(f"Não encontrado: {termo}")
                continue

            log(f"Encontrado ({len(areas)}x): {termo}")
            for area in areas:
                page.add_redact_annot(area, fill=(0, 0, 0))

        # Uma vez por página, depois de marcar todos os termos
        page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_PIXELS, graphics=pymupdf.PDF_REDACT_LINE_ART_REMOVE_IF_TOUCHED)

        if ao_avancar:
            ao_avancar(page.number + 1, total)

    doc.scrub() # Limpa os metadados
    doc.save(saida, garbage=4, deflate=True) # Garbage limpa o pdf, deflate comprime streams