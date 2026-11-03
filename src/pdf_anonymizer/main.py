INTERFACE = "qt"

def main() -> None:
    import sys

    escolha = INTERFACE
    for argumento in sys.argv[1:]:
        if argumento.startswith("--gui="):
            escolha = argumento.removeprefix("--gui=")

    # Importa só a interface escolhida, para não carregar o Qt à toa
    if escolha == "qt":
        from pdf_anonymizer.gui_qt import main as abrir_interface
    elif escolha == "antiga":
        from pdf_anonymizer.gui_tkinter import main as abrir_interface
    else:
        raise SystemExit(f"Interface desconhecida: {escolha}")

    abrir_interface()
