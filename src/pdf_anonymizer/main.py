from pdf_anonymizer.anonymizer import censurar_dados, abrir_arquivo

def main() -> None:
    
    arquivo = r"C:\Users\Arthur Locatelli\Downloads\Teste.pdf"
    dados = []

    doc = abrir_arquivo(arquivo)
    censurar_dados(doc,dados)