import pymupdf

def abrir_arquivo(arquivo: str) -> pymupdf.Document:
    doc = pymupdf.open(arquivo)
    return doc

def censurar_dados(doc: pymupdf.Document, lista_string: list) -> None:
    for page in doc:
        print("Página: ", page.number)
        for string in lista_string:

            print("Dado a ser ocultado: ", string)
            lista_areas = page.search_for(string)

            if not lista_areas:
                print("Dado não encontrado")
                continue

            print("Dado encontrado")
            
            for area in lista_areas:
                page.add_redact_annot(area, fill=(0, 0, 0))

        page.apply_redactions()

    doc.save("data/documento_censurado.pdf")

    return