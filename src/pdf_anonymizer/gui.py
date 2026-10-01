import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from pdf_anonymizer.anonymizer import abrir_arquivo, censurar_dados

class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("PDF Anonymizer")
        root.minsize(440, 380)

        self.arquivos: list[Path] = []

        # Fila para a thread de processamento mandar mensagens para a interface.
        # O Tkinter só pode ser atualizado pela thread principal.
        self.fila: queue.Queue = queue.Queue()

        frame = ttk.Frame(root, padding=16)
        frame.pack(fill="both", expand=True)

        ttk.Button(frame, text="Selecionar PDFs...", command=self.selecionar).pack(anchor="w")
        self.rotulo_arquivos = ttk.Label(frame, text="Nenhum arquivo selecionado", foreground="#666")
        self.rotulo_arquivos.pack(anchor="w", pady=(4, 0))

        ttk.Label(frame, text="Dados a ocultar (um por linha):").pack(anchor="w", pady=(16, 4))
        self.termos = tk.Text(frame, height=8, wrap="none")
        self.termos.pack(fill="both", expand=True)

        self.botao = ttk.Button(frame, text="Anonimizar", command=self.iniciar)
        self.botao.pack(pady=12)

        self.progresso = ttk.Progressbar(frame, mode="determinate", maximum=100)
        self.progresso.pack(fill="x")

        self.status = ttk.Label(frame, text="", foreground="#666")
        self.status.pack(anchor="w", pady=(6, 0))

    def selecionar(self) -> None:
        caminhos = filedialog.askopenfilenames(filetypes=[("PDF", "*.pdf")])
        if not caminhos:
            return

        self.arquivos = [Path(c) for c in caminhos]
        if len(self.arquivos) == 1:
            self.rotulo_arquivos.config(text=self.arquivos[0].name)
        else:
            self.rotulo_arquivos.config(text=f"{len(self.arquivos)} arquivos selecionados")

    def iniciar(self) -> None:
        termos = [t.strip() for t in self.termos.get("1.0", "end").splitlines() if t.strip()]

        if not self.arquivos:
            messagebox.showwarning("Atenção", "Selecione pelo menos um PDF.")
            return
        if not termos:
            messagebox.showwarning("Atenção", "Informe pelo menos um dado a ocultar.")
            return

        self.botao.config(state="disabled")
        self.progresso.config(value=0)

        # O processamento roda em outra thread para a janela não travar
        threading.Thread(
            target=self.processar, args=(list(self.arquivos), termos), daemon=True
        ).start()
        self.root.after(100, self.atualizar)

    def processar(self, arquivos: list[Path], termos: list[str]) -> None:
        n = len(arquivos)
        erros = []

        for i, arquivo in enumerate(arquivos):
            # Salva ao lado do original: extrato.pdf -> extrato_censurado.pdf
            saida = arquivo.with_name(f"{arquivo.stem}_censurado.pdf")
            self.fila.put(("status", f"Arquivo {i + 1} de {n}: {arquivo.name}"))

            try:
                doc = abrir_arquivo(str(arquivo))
                censurar_dados(
                    doc,
                    termos,
                    str(saida),
                    log=lambda _: None,
                    # Progresso geral: arquivos concluídos + fração do arquivo atual
                    ao_avancar=lambda atual, total, i=i: self.fila.put(
                        ("progresso", (i + atual / total) / n * 100)
                    ),
                )
                doc.close()
            except Exception as erro:
                # Um arquivo com problema não interrompe os demais
                erros.append(f"{arquivo.name}: {erro}")

            self.fila.put(("progresso", (i + 1) / n * 100))

        self.fila.put(("fim", (n, erros)))

    def atualizar(self) -> None:
        # Lê as mensagens da thread de processamento e atualiza a interface
        try:
            while True:
                tipo, valor = self.fila.get_nowait()

                if tipo == "status":
                    self.status.config(text=valor)
                elif tipo == "progresso":
                    self.progresso.config(value=valor)
                elif tipo == "fim":
                    self.finalizar(*valor)
                    return
        except queue.Empty:
            pass

        self.root.after(100, self.atualizar)

    def finalizar(self, n: int, erros: list[str]) -> None:
        self.botao.config(state="normal")
        concluidos = n - len(erros)
        self.status.config(text=f"{concluidos} de {n} arquivo(s) anonimizado(s)")

        mensagem = (
            f"{concluidos} de {n} arquivo(s) anonimizado(s).\n\n"
            "Os arquivos foram salvos ao lado dos originais, com o sufixo _censurado.\n"
            "Revise os documentos antes de compartilhá-los."
        )
        if erros:
            mensagem += "\n\nFalharam:\n" + "\n".join(erros)
            messagebox.showwarning("Concluído com erros", mensagem)
        else:
            messagebox.showinfo("Concluído", mensagem)

def main() -> None:
    root = tk.Tk()
    App(root)
    root.mainloop()

if __name__ == "__main__":
    main()