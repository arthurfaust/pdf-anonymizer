import queue
import threading
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from pdf_anonymizer.anonymizer import abrir_arquivo, censurar_dados

# Categorias de dados e os exemplos exibidos como placeholder.
# Cada exemplo gera um campo inicial; o botão + adiciona campos extras.
CATEGORIAS = [
    ("Nome", ["José"]),
    ("Sobrenome", ["da Silva", "Sauro"]),
    ("Contato / Telefone / e-mail)", ["(47) 98765-4321", "jose@email.com"]),
    ("Identificador / CPF / CNPJ)", ["123.456.789-00"]),
    ("Número de Conta / Cartão", ["BR8-123456","1234 5678 9101 1121"]),
    ("Endereço / CEP / ZIP Code", ["Rua Maracujá 123", "Osasco SP", "89220-878"]),
    ("Outros dados", ["FAUST SOLUÇÔES TRIBUTÁRIAS LTDA"]),
]

AVISO = (
    "Como o programa encontra os dados:\n\n"
    "• Maiúsculas, acentos, pontuação e espaços não fazem diferença. "
    "\"jose da silva\" encontra \"JOSÉ DA SILVA\", e \"12345678900\" "
    "encontra \"123.456.789-00\".\n\n"
    "• O dado precisa aparecer inteiro, com as palavras na mesma ordem. "
    "Se você digitar \"José da Silva\", um trecho com só \"Silva\" ou "
    "\"J. Silva\" continuará visível. Para ocultá-lo, adicione essa "
    "variação em outro campo com o botão +.\n\n"
    "• Só palavras completas são ocultadas: \"Silva\" não oculta \"Silveira\".\n\n"
    "• Evite termos curtos e comuns sozinhos, como \"da\" ou \"Rua\". "
    "Todas as ocorrências deles no documento seriam ocultadas.\n\n"
    "• Em páginas escaneadas ou fotografadas, o texto é lido por OCR e "
    "pode haver falhas. Sempre revise o resultado.\n\n"
    "Os textos em cinza nos campos são apenas exemplos e não serão usados."
)

class CampoComPlaceholder(ttk.Entry):
    """Entry que mostra um texto de exemplo em cinza enquanto está vazio."""

    def __init__(self, master, placeholder: str = "", **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.placeholder = placeholder
        self.mostrando_placeholder = False

        self.bind("<FocusIn>", self._ao_focar)
        self.bind("<FocusOut>", self._ao_desfocar)
        self._mostrar_placeholder()

    def _mostrar_placeholder(self) -> None:
        if self.placeholder and not self.get():
            self.mostrando_placeholder = True
            self.configure(style="Placeholder.TEntry")
            self.insert(0, self.placeholder)

    def _ao_focar(self, _evento) -> None:
        if self.mostrando_placeholder:
            self.delete(0, "end")
            self.configure(style="TEntry")
            self.mostrando_placeholder = False

    def _ao_desfocar(self, _evento) -> None:
        self._mostrar_placeholder()

    def valor(self) -> str:
        # O placeholder nunca é tratado como dado digitado
        return "" if self.mostrando_placeholder else self.get().strip()

class GrupoDeCampos(ttk.Frame):
    """Título de uma categoria + lista de campos, cada um com seu botão +."""

    def __init__(self, master, titulo: str, exemplos: list[str]) -> None:
        super().__init__(master)
        ttk.Label(self, text=titulo).pack(anchor="w", pady=(10, 2))

        self.linhas: list[tuple[ttk.Frame, CampoComPlaceholder]] = []
        for exemplo in exemplos:
            self.adicionar_campo(placeholder=exemplo)

    def adicionar_campo(self, placeholder: str = "", abaixo_de: ttk.Frame | None = None) -> None:
        linha = ttk.Frame(self)
        campo = CampoComPlaceholder(linha, placeholder=placeholder, width=40)
        campo.pack(side="left")
        ttk.Button(
            linha,
            text="+",
            width=3,
            command=lambda: self.adicionar_campo(abaixo_de=linha),
        ).pack(side="left", padx=(6, 0))

        if abaixo_de is None:
            linha.pack(anchor="w", pady=2)
            self.linhas.append((linha, campo))
        else:
            # Novo campo entra logo abaixo daquele cujo + foi clicado
            linha.pack(anchor="w", pady=2, after=abaixo_de)
            indice = next(i for i, (l, _) in enumerate(self.linhas) if l is abaixo_de)
            self.linhas.insert(indice + 1, (linha, campo))
            campo.focus_set()

    def valores(self) -> list[str]:
        return [c.valor() for _, c in self.linhas if c.valor()]

class AreaRolavel(ttk.Frame):
    """Frame com barra de rolagem vertical (os campos podem crescer bastante)."""

    def __init__(self, master) -> None:
        super().__init__(master)
        fundo = ttk.Style(self).lookup("TFrame", "background")
        self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0, background=fundo)
        barra = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.conteudo = ttk.Frame(self.canvas)

        janela = self.canvas.create_window((0, 0), window=self.conteudo, anchor="nw")
        self.canvas.configure(yscrollcommand=barra.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")

        self.conteudo.bind(
            "<Configure>",
            lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(janela, width=e.width))

        # Roda do mouse (Windows/macOS usam <MouseWheel>; Linux usa botões 4 e 5)
        self.bind_all("<MouseWheel>", self._rolar, add="+")
        self.bind_all("<Button-4>", self._rolar, add="+")
        self.bind_all("<Button-5>", self._rolar, add="+")

    def _rolar(self, evento) -> None:
        # Só rola se o cursor estiver sobre esta área
        try:
            sob_cursor = self.winfo_containing(evento.x_root, evento.y_root)
        except (KeyError, tk.TclError):
            return
        if sob_cursor is None or not str(sob_cursor).startswith(str(self)):
            return

        if evento.num == 4:
            passo = -1
        elif evento.num == 5:
            passo = 1
        else:
            passo = -1 if evento.delta > 0 else 1
        self.canvas.yview_scroll(passo, "units")

class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("PDF Anonymizer")
        root.geometry("800x760")
        root.minsize(680, 560)

        self.arquivos: list[Path] = []
        self.pasta_saida: Path | None = None  # None = salvar ao lado dos originais

        # Fila para a thread de processamento mandar mensagens para a interface.
        # O Tkinter só pode ser atualizado pela thread principal.
        self.fila: queue.Queue = queue.Queue()

        estilo = ttk.Style(root)
        estilo.configure("Placeholder.TEntry", foreground="#9a9a9a")
        self.fonte_negrito = tkfont.nametofont("TkDefaultFont").copy()
        self.fonte_negrito.configure(weight="bold")

        frame = ttk.Frame(root, padding=16)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(5, weight=1)

        # Arquivos de entrada
        self.botao_pdfs = ttk.Button(frame, text="Selecionar PDFs...", command=self.selecionar)
        self.botao_pdfs.grid(row=0, column=0, sticky="w")
        self.rotulo_arquivos = ttk.Label(
            frame, text="Nenhum arquivo selecionado", foreground="#666", wraplength=740
        )
        self.rotulo_arquivos.grid(row=1, column=0, sticky="w", pady=(4, 12))

        # Pasta de saída
        self.botao_pasta = ttk.Button(
            frame, text="Selecionar pasta de saída...", command=self.selecionar_pasta
        )
        self.botao_pasta.grid(row=2, column=0, sticky="w")
        self.rotulo_pasta = ttk.Label(
            frame, text="Mesma pasta dos PDFs originais", foreground="#666", wraplength=740
        )
        self.rotulo_pasta.grid(row=3, column=0, sticky="w", pady=(4, 12))

        ttk.Label(frame, text="Dados a ocultar:", font=self.fonte_negrito).grid(
            row=4, column=0, sticky="w"
        )

        # Campos (esquerda, com rolagem) + aviso (direita)
        meio = ttk.Frame(frame)
        meio.grid(row=5, column=0, sticky="nsew")
        meio.columnconfigure(0, weight=1)
        meio.rowconfigure(0, weight=1)

        area = AreaRolavel(meio)
        area.grid(row=0, column=0, sticky="nsew")

        self.grupos: list[GrupoDeCampos] = []
        for titulo, exemplos in CATEGORIAS:
            grupo = GrupoDeCampos(area.conteudo, titulo, exemplos)
            grupo.pack(fill="x", anchor="w")
            self.grupos.append(grupo)

        aviso = ttk.LabelFrame(meio, text=" Importante! ", padding=12)
        aviso.grid(row=0, column=1, sticky="n", padx=(16, 0), pady=(10, 0))
        ttk.Label(aviso, text=AVISO, wraplength=270, justify="left").pack(anchor="w")

        # Ação e progresso
        self.botao = ttk.Button(frame, text="Anonimizar", command=self.iniciar)
        self.botao.grid(row=6, column=0, pady=12)

        self.progresso = ttk.Progressbar(frame, mode="determinate", maximum=100)
        self.progresso.grid(row=7, column=0, sticky="ew")

        self.status = ttk.Label(frame, text="", foreground="#666")
        self.status.grid(row=8, column=0, sticky="w", pady=(6, 0))

    def selecionar(self) -> None:
        caminhos = filedialog.askopenfilenames(filetypes=[("PDF", "*.pdf")])
        if not caminhos:
            return

        self.arquivos = [Path(c) for c in caminhos]
        nomes = [a.name for a in self.arquivos]
        if len(nomes) > 3:
            texto = "  ".join(nomes[:3]) + f"  e mais {len(nomes) - 3} arquivo(s)"
        else:
            texto = "  ".join(nomes)
        self.rotulo_arquivos.config(text=texto)

    def selecionar_pasta(self) -> None:
        pasta = filedialog.askdirectory()
        if not pasta:
            return
        self.pasta_saida = Path(pasta)
        self.rotulo_pasta.config(text=str(self.pasta_saida))

    def coletar_termos(self) -> list[str]:
        # Junta os dados de todos os campos, sem repetições e mantendo a ordem
        termos = [valor for grupo in self.grupos for valor in grupo.valores()]
        return list(dict.fromkeys(termos))

    def iniciar(self) -> None:
        termos = self.coletar_termos()

        if not self.arquivos:
            messagebox.showwarning("Atenção", "Selecione pelo menos um PDF.")
            return
        if not termos:
            messagebox.showwarning("Atenção", "Preencha pelo menos um dado a ocultar.")
            return

        for botao in (self.botao, self.botao_pdfs, self.botao_pasta):
            botao.config(state="disabled")
        self.progresso.config(value=0)

        # O processamento roda em outra thread para a janela não travar
        threading.Thread(
            target=self.processar,
            args=(list(self.arquivos), termos, self.pasta_saida),
            daemon=True,
        ).start()
        self.root.after(100, self.atualizar)

    def processar(self, arquivos: list[Path], termos: list[str], pasta: Path | None) -> None:
        n = len(arquivos)
        erros = []

        for i, arquivo in enumerate(arquivos):
            # extrato.pdf -> extrato_censurado.pdf (na pasta escolhida ou ao lado do original)
            destino = pasta if pasta is not None else arquivo.parent
            saida = destino / f"{arquivo.stem}_censurado.pdf"
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

        self.fila.put(("fim", (n, erros, pasta)))

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

    def finalizar(self, n: int, erros: list[str], pasta: Path | None) -> None:
        for botao in (self.botao, self.botao_pdfs, self.botao_pasta):
            botao.config(state="normal")

        concluidos = n - len(erros)
        self.status.config(text=f"{concluidos} de {n} arquivo(s) anonimizado(s)")

        local = f"na pasta:\n{pasta}" if pasta else "ao lado dos originais"
        mensagem = (
            f"{concluidos} de {n} arquivo(s) anonimizado(s).\n\n"
            f"Os arquivos foram salvos {local}, com o sufixo _censurado.\n"
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
