import pymupdf

def abrir_arquivo(arquivo: str) -> pymupdf.Document:
    doc = pymupdf.open(arquivo)
    return doc

def censurar_dados(doc: pymupdf.Document, termos: list[str]) -> None:
    for page in doc:
        print(f"Página [{page.number}]")
        
        textpage = None

        if not page.get_text().strip():
            print("Página sem texto, aplicando OCR...")
            textpage = page.get_textpage_ocr(language="por", dpi=600, full=True)

            if page.number in [0]: 
                texto = page.get_text(textpage=textpage)
                print(texto)

        for termo in termos:
            areas = page.search_for(termo, textpage=textpage)

            if not areas:
                print(f"Não encontrado: {termo}")
                continue

            print(f"Encontrado ({len(areas)}x): {termo}")
            for area in areas:
                page.add_redact_annot(area, fill=(0, 0, 0))

        # Uma vez por página, depois de marcar todos os termos
        page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_PIXELS)

    doc.scrub() # Limpa os metadados
    doc.save("data/documento_censurado.pdf", garbage=4, deflate=True) # Garbage limpa o pdf, deflate comprime streams

    return