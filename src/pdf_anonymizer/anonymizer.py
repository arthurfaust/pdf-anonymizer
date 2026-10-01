import pymupdf
import unicodedata
import pytesseract
import re
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def abrir_arquivo(arquivo: str) -> pymupdf.Document:
    doc = pymupdf.open(arquivo)
    return doc

def normalizar(s: str) -> str: # José, Sep-28
    s = unicodedata.normalize("NFD", s) # José -> Jose´, Sep-28 
    s = "".join(c for c in s if unicodedata.category(c) != "Mn") # Jose´ -> Jose, Sep-28
    return "".join(c for c in s.upper() if c.isalnum()) # Jose -> JOSE, Sep-28 -> SEP28

def ocr_palavras(page: pymupdf.Page, dpi: int = 400, limite: int = 170, psm: int = 11, margem: float = 1.5,) -> list[tuple[pymupdf.Rect, str]]:
    pix = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY) # Renderiza a página em escala de cinza
    tabela = bytes(255 if i > limite else 0 for i in range(256)) 
    img = Image.frombytes("L", (pix.width, pix.height), pix.samples.translate(tabela))

    dados = pytesseract.image_to_data(img, lang="por", config=f"--psm {psm}", output_type=pytesseract.Output.DICT)

    # Pixels da imagem -> pontos da página original
    escala = pymupdf.Matrix(72 / dpi, 72 / dpi) * page.derotation_matrix
    palavras = []

    for texto, x, y, w, h in zip(dados["text"], dados["left"], dados["top"], dados["width"], dados["height"]):
        if not texto.strip():
            continue

        rect = pymupdf.Rect(x, y, x + w, y + h) * escala
        n = len(texto)

        for m in re.finditer(r"\w+", texto):
            x0 = rect.x0 + rect.width * m.start() / n - margem
            x1 = rect.x0 + rect.width * m.end() / n + margem
            palavras.append((pymupdf.Rect(x0, rect.y0, x1, rect.y1), m.group()))
    return palavras

def buscar_termo(palavras: list[tuple[pymupdf.Rect, str]], termo: str) -> list[pymupdf.Rect]:
    alvo = [normalizar(p) for p in re.findall(r"\w+", termo)]
    textos = [normalizar(t) for _, t in palavras]
    n = len(alvo)

    areas = []
    for i in range(len(textos) - n + 1):
        if textos[i:i + n] == alvo:
            areas.extend(rect for rect, _ in palavras[i:i + n])
    return areas

def censurar_dados(doc: pymupdf.Document, termos: list[str], saida: str) -> None:
    for page in doc:
        print(f"Página [{page.number}]")
        
        palavras = None

        if not page.get_text().strip() or page.get_images():
            print("Página sem texto, aplicando OCR...")
        
            palavras = ocr_palavras(page)

        for termo in termos:
            areas = page.search_for(termo)

            if palavras is not None:
                areas += buscar_termo(palavras, termo)
                
            if not areas:
                print(f"Não encontrado: {termo}")
                continue

            print(f"Encontrado ({len(areas)}x): {termo}")
            for area in areas:
                page.add_redact_annot(area, fill=(0, 0, 0))

        # Uma vez por página, depois de marcar todos os termos
        page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_PIXELS)

    doc.scrub() # Limpa os metadados
    doc.save(saida, garbage=4, deflate=True) # Garbage limpa o pdf, deflate comprime streams