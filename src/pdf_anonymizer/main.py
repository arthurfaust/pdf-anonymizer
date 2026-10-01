from pdf_anonymizer.anonymizer import censurar_dados, abrir_arquivo

def main() -> None:
    
    arquivo = r".pdf"
    arquivo_censurado = ".pdf"
    dados = []

    doc = abrir_arquivo(arquivo)
    censurar_dados(doc,dados,arquivo_censurado)