import sys
from pathlib import Path

from PySide6.QtCore import QThread, QUrl, Qt, Signal
from PySide6.QtGui import QDesktopServices, QFont
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from pdf_anonymizer.anonymizer import abrir_arquivo, censurar_dados

CATEGORIAS = [
    ("Nome", ["José"]),
    ("Sobrenome", ["Ferreira", "Sauro"]),
    ("Contato (telefone / e-mail)", ["(47) 98765-4321", "jose@email.com"]),
    ("Identificador (CPF / CNPJ)", ["123.456.789-00"]),
    ("Número de conta / cartão", ["BR8-123456", "1234 5678 9101 1121"]),
    ("Endereço / CEP / ZIP Code", ["Rua Maracujá 123", "Osasco SP", "89220-878"]),
    ("Outros dados", ["FAUST SOLUÇÕES TRIBUTÁRIAS LTDA"]),
]

AVISO_CURTO = "Revise sempre os documentos gerados antes de compartilhá-los."

AJUDA = (
    "• Maiúsculas, acentos, pontuação e espaços não fazem diferença. "
    "\"jose da silva\" encontra \"JOSÉ DA SILVA\", e \"12345678900\" "
    "encontra \"123.456.789-00\".\n\n"
    "• O dado precisa aparecer inteiro, com as palavras na mesma ordem. "
    "Se você digitar \"José da Silva\", um trecho com só \"Silva\" ou "
    "\"J. Silva\" continuará visível. Para ocultá-lo, adicione essa "
    "variação em outro campo.\n\n"
    "• Só palavras completas são ocultadas: \"Silva\" não oculta \"Silveira\".\n\n"
    "• Evite termos curtos e comuns sozinhos, como \"da\" ou \"Rua\". "
    "Todas as ocorrências deles no documento seriam ocultadas.\n\n"
    "• Em páginas escaneadas ou fotografadas, o texto é lido por OCR e "
    "pode haver falhas. Sempre revise o resultado."
)

SUFIXO = "_censurado"

TEMAS = {
    "claro": {
        "fundo": "#f3f3f3",
        "superficie": "#ffffff",
        "borda": "#e0e0e0",
        "borda_forte": "#b8b8b8",
        "texto": "#1b1b1b",
        "secundario": "#616161",
        "campo": "#ffffff",
        "botao": "#fbfbfb",
        "botao_hover": "#f0f0f0",
        "acento": "#005fb8",
        "acento_hover": "#1a6fc2",
        "acento_suave": "#e5f0fa",
        "texto_acento": "#ffffff",
        "sucesso": "#0f7b0f",
        "erro": "#c42b1c",
    },
    "escuro": {
        "fundo": "#202020",
        "superficie": "#2b2b2b",
        "borda": "#3a3a3a",
        "borda_forte": "#5a5a5a",
        "texto": "#f0f0f0",
        "secundario": "#a8a8a8",
        "campo": "#1f1f1f",
        "botao": "#373737",
        "botao_hover": "#424242",
        "acento": "#60cdff",
        "acento_hover": "#7ad5ff",
        "acento_suave": "#1d3a4d",
        "texto_acento": "#000000",
        "sucesso": "#6ccb5f",
        "erro": "#ff99a4",
    },
}

ESTILO = """
QWidget {{ color: {texto}; }}
#fundo {{ background: {fundo}; }}
#cabecalho {{ background: {superficie}; border-bottom: 1px solid {borda}; }}
#rodape {{ background: {superficie}; border-top: 1px solid {borda}; }}
#cartao {{ background: {superficie}; border: 1px solid {borda}; border-radius: 8px; }}
#cartao QLabel, #cabecalho QLabel, #rodape QLabel {{ background: transparent; }}

#titulo {{ font-size: 18pt; font-weight: 600; }}
#tituloCartao {{ font-size: 13pt; font-weight: 600; }}
#destaque {{ font-weight: 600; }}
#secundario {{ color: {secundario}; }}
#dica {{ color: {secundario}; font-size: 9pt; }}
#cartao #etapa {{
    background: {acento_suave}; color: {acento}; font-weight: 700;
    border-radius: 14px; min-width: 28px; max-width: 28px; min-height: 28px; max-height: 28px;
}}
#status[estado="sucesso"] {{ color: {sucesso}; }}
#status[estado="erro"] {{ color: {erro}; }}

QLineEdit {{
    background: {campo}; border: 1px solid {borda}; border-bottom-color: {borda_forte};
    border-radius: 4px; padding: 5px 8px; selection-background-color: {acento};
}}
QLineEdit:focus {{ border-bottom: 2px solid {acento}; }}

QPushButton {{
    background: {botao}; border: 1px solid {borda}; border-radius: 4px; padding: 6px 14px;
}}
QPushButton:hover {{ background: {botao_hover}; }}
QPushButton:disabled {{ color: {secundario}; }}
QPushButton#primario {{
    background: {acento}; color: {texto_acento}; border: none; padding: 8px 28px; font-weight: 600;
}}
QPushButton#primario:hover {{ background: {acento_hover}; }}
QPushButton#primario:disabled {{ background: {borda}; color: {secundario}; }}
QPushButton#link {{ background: transparent; border: none; color: {acento}; padding: 2px 0; }}
QPushButton#link:hover {{ text-decoration: underline; }}

QToolButton#remover {{
    background: transparent; border: none; border-radius: 4px; color: {secundario};
    min-width: 28px; min-height: 28px;
}}
QToolButton#remover:hover {{ background: {botao_hover}; color: {texto}; }}

#zonaArquivos {{ background: {fundo}; border: 1px dashed {borda_forte}; border-radius: 6px; }}
#zonaArquivos[arrastando="true"] {{ background: {acento_suave}; border-color: {acento}; }}
#zonaArquivos QLabel {{ background: transparent; }}

QProgressBar {{ background: {borda}; border: none; border-radius: 2px; max-height: 4px; }}
QProgressBar::chunk {{ background: {acento}; border-radius: 2px; }}

QScrollArea {{ background: transparent; border: none; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {borda_forte}; border-radius: 3px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{
    background: none; height: 0;
}}
"""

def _repolir(widget: QWidget) -> None:
    # Reaplica o estilo depois de mudar uma propriedade usada nos seletores
    widget.style().unpolish(widget)
    widget.style().polish(widget)

def _rotulo(texto: str, nome: str = "") -> QLabel:
    rotulo = QLabel(texto)
    if nome:
        rotulo.setObjectName(nome)
    return rotulo

def _botao_remover(ao_clicar) -> QToolButton:
    botao = QToolButton()
    botao.setObjectName("remover")
    botao.setText("✕")
    botao.setCursor(Qt.CursorShape.PointingHandCursor)
    botao.setToolTip("Remover")
    botao.clicked.connect(ao_clicar)
    return botao

def _botao_link(texto: str, ao_clicar) -> QPushButton:
    botao = QPushButton(texto)
    botao.setObjectName("link")
    botao.setCursor(Qt.CursorShape.PointingHandCursor)
    botao.clicked.connect(ao_clicar)
    return botao

def _tamanho_legivel(caminho: Path) -> str:
    try:
        tamanho = caminho.stat().st_size
    except OSError:
        return ""
    for unidade in ("B", "KB", "MB"):
        if tamanho < 1024:
            return f"{tamanho:.0f} {unidade}"
        tamanho /= 1024
    return f"{tamanho:.1f} GB"

class Cartao(QFrame):
    """Bloco com borda arredondada, número da etapa, título e descrição."""

    def __init__(self, numero: int, titulo: str, descricao: str) -> None:
        super().__init__()
        self.setObjectName("cartao")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(16)

        self.cabecalho = QHBoxLayout()
        self.cabecalho.setSpacing(12)
        etapa = _rotulo(str(numero), "etapa")
        etapa.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cabecalho.addWidget(etapa, alignment=Qt.AlignmentFlag.AlignTop)
        textos = QVBoxLayout()
        textos.setSpacing(0)
        textos.addWidget(_rotulo(titulo, "tituloCartao"))
        textos.addWidget(_rotulo(descricao, "secundario"))
        self.cabecalho.addLayout(textos, stretch=1)
        layout.addLayout(self.cabecalho)

        self.corpo = QVBoxLayout()
        self.corpo.setSpacing(8)
        layout.addLayout(self.corpo)

class ZonaArquivos(QFrame):
    """Lista dos PDFs escolhidos; também aceita arquivos arrastados do Explorer."""

    arquivos_soltos = Signal(list)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("zonaArquivos")
        self.setAcceptDrops(True)
        self.layout_ = QVBoxLayout(self)
        self.layout_.setContentsMargins(12, 8, 8, 8)
        self.layout_.setSpacing(0)

    def _pdfs(self, evento) -> list[Path]:
        urls = evento.mimeData().urls() if evento.mimeData().hasUrls() else []
        caminhos = [Path(u.toLocalFile()) for u in urls if u.isLocalFile()]
        return [c for c in caminhos if c.suffix.lower() == ".pdf"]

    def _destacar(self, ativo: bool) -> None:
        self.setProperty("arrastando", ativo)
        _repolir(self)

    def dragEnterEvent(self, evento) -> None:
        if self._pdfs(evento):
            evento.acceptProposedAction()
            self._destacar(True)

    def dragLeaveEvent(self, _evento) -> None:
        self._destacar(False)

    def dropEvent(self, evento) -> None:
        self._destacar(False)
        self.arquivos_soltos.emit(self._pdfs(evento))

class GrupoDeCampos(QWidget):
    """Título de uma categoria e lista de campos removíveis."""

    def __init__(self, titulo: str, exemplos: list[str]) -> None:
        super().__init__()
        self.exemplos = exemplos
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(_rotulo(titulo, "destaque"))

        self.lista = QVBoxLayout()
        self.lista.setSpacing(4)
        layout.addLayout(self.lista)
        layout.addWidget(
            _botao_link("+  Adicionar", lambda: self.adicionar_campo()), alignment=Qt.AlignmentFlag.AlignLeft
        )

        self.linhas: list[tuple[QWidget, QLineEdit]] = []
        self.adicionar_campo(focar=False)

    def adicionar_campo(self, abaixo_de: QWidget | None = None, focar: bool = True) -> None:
        linha = QWidget()
        layout = QHBoxLayout(linha)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        campo = QLineEdit()
        # Cada campo novo sugere o próximo exemplo da categoria
        if len(self.linhas) < len(self.exemplos):
            campo.setPlaceholderText(f"ex.: {self.exemplos[len(self.linhas)]}")
        # Enter cria um novo campo logo abaixo
        campo.returnPressed.connect(lambda: self.adicionar_campo(abaixo_de=linha))
        layout.addWidget(campo)
        layout.addWidget(_botao_remover(lambda: self.remover_campo(linha)))

        if abaixo_de is None:
            indice = len(self.linhas)
        else:
            indice = next(i for i, (l, _) in enumerate(self.linhas) if l is abaixo_de) + 1
        self.lista.insertWidget(indice, linha)
        self.linhas.insert(indice, (linha, campo))
        if focar:
            campo.setFocus()

    def remover_campo(self, linha: QWidget) -> None:
        # O último campo nunca some, só é esvaziado
        if len(self.linhas) == 1:
            self.linhas[0][1].clear()
            return
        self.linhas = [(l, c) for l, c in self.linhas if l is not linha]
        linha.deleteLater()

    def valores(self) -> list[str]:
        return [c.text().strip() for _, c in self.linhas if c.text().strip()]

class Processamento(QThread):
    """Anonimiza os arquivos fora da thread da interface, para a janela não travar."""

    status = Signal(str)
    progresso = Signal(float)
    fim = Signal(int, list, object)

    def __init__(self, arquivos: list[Path], termos: list[str], pasta: Path | None) -> None:
        super().__init__()
        self.arquivos = arquivos
        self.termos = termos
        self.pasta = pasta

    def run(self) -> None:
        n = len(self.arquivos)
        erros = []

        for i, arquivo in enumerate(self.arquivos):
            # extrato.pdf -> extrato_censurado.pdf (na pasta escolhida ou ao lado do original)
            destino = self.pasta if self.pasta is not None else arquivo.parent
            saida = destino / f"{arquivo.stem}{SUFIXO}.pdf"
            self.status.emit(f"Arquivo {i + 1} de {n}: {arquivo.name}")

            try:
                doc = abrir_arquivo(str(arquivo))
                censurar_dados(
                    doc,
                    self.termos,
                    str(saida),
                    log=lambda _: None,
                    # Progresso geral: arquivos concluídos + fração do arquivo atual
                    ao_avancar=lambda atual, total, i=i: self.progresso.emit((i + atual / total) / n * 100),
                )
                doc.close()
            except Exception as erro:
                # Um arquivo com problema não interrompe os demais
                erros.append(f"{arquivo.name}: {erro}")

            self.progresso.emit((i + 1) / n * 100)

        destino = self.pasta if self.pasta is not None else self.arquivos[0].parent
        self.fim.emit(n, erros, destino)

class Janela(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PDF Anonymizer")
        self.setMinimumSize(720, 560)

        self.arquivos: list[Path] = []
        self.pasta_saida: Path | None = None  # None = salvar ao lado dos originais
        self.pasta_resultado: Path | None = None
        self.erros: list[str] = []
        self.trabalho: Processamento | None = None

        raiz = QWidget()
        raiz.setObjectName("fundo")
        self.setCentralWidget(raiz)
        layout = QVBoxLayout(raiz)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._montar_cabecalho())

        rolagem = QScrollArea()
        rolagem.setWidgetResizable(True)
        rolagem.setFrameShape(QFrame.Shape.NoFrame)
        conteudo = QWidget()
        conteudo.setObjectName("fundo")
        corpo = QVBoxLayout(conteudo)
        corpo.setContentsMargins(24, 20, 24, 20)
        corpo.setSpacing(16)
        corpo.addWidget(self._montar_arquivos())
        corpo.addWidget(self._montar_dados())
        corpo.addStretch()
        rolagem.setWidget(conteudo)
        layout.addWidget(rolagem, stretch=1)

        layout.addWidget(self._montar_rodape())
        self.aplicar_tema()

    # ---------- Montagem ----------

    def _montar_cabecalho(self) -> QWidget:
        cabecalho = QFrame()
        cabecalho.setObjectName("cabecalho")
        layout = QHBoxLayout(cabecalho)
        layout.setContentsMargins(24, 14, 24, 14)
        layout.setSpacing(16)
        layout.addWidget(_rotulo("PDF Anonymizer", "titulo"))
        subtitulo = _rotulo("Oculte dados pessoais em documentos PDF", "secundario")
        layout.addWidget(subtitulo, alignment=Qt.AlignmentFlag.AlignBottom)
        layout.addStretch()
        self.tema_escuro = QCheckBox("Tema escuro")
        self.tema_escuro.toggled.connect(self.aplicar_tema)
        layout.addWidget(self.tema_escuro)
        return cabecalho

    def _montar_arquivos(self) -> QWidget:
        cartao = Cartao(1, "Arquivos", "Escolha os PDFs e onde salvar as cópias anonimizadas.")
        self.botao_pdfs = QPushButton("Adicionar PDFs…")
        self.botao_pdfs.clicked.connect(self.selecionar)
        cartao.cabecalho.addWidget(self.botao_pdfs, alignment=Qt.AlignmentFlag.AlignTop)

        self.zona = ZonaArquivos()
        self.zona.arquivos_soltos.connect(self.adicionar_arquivos)
        cartao.corpo.addWidget(self.zona)
        self._mostrar_arquivos()

        saida = QHBoxLayout()
        saida.setSpacing(12)
        saida.addWidget(_rotulo("Salvar em", "destaque"))
        self.rotulo_pasta = _rotulo("", "secundario")
        saida.addWidget(self.rotulo_pasta, stretch=1)
        self.botao_pasta_original = _botao_link("Usar pasta dos originais", self.usar_pasta_original)
        saida.addWidget(self.botao_pasta_original)
        self.botao_pasta = QPushButton("Alterar…")
        self.botao_pasta.clicked.connect(self.selecionar_pasta)
        saida.addWidget(self.botao_pasta)
        cartao.corpo.addSpacing(4)
        cartao.corpo.addLayout(saida)
        self._mostrar_pasta()
        return cartao

    def _montar_dados(self) -> QWidget:
        cartao = Cartao(
            2, "Dados a ocultar", "Digite os dados como aparecem no documento. Enter cria outro campo."
        )
        cartao.cabecalho.addWidget(
            _botao_link("Como a busca funciona", self.mostrar_ajuda), alignment=Qt.AlignmentFlag.AlignTop
        )

        grade = QGridLayout()
        grade.setHorizontalSpacing(24)
        grade.setVerticalSpacing(16)
        grade.setColumnStretch(0, 1)
        grade.setColumnStretch(1, 1)
        self.grupos: list[GrupoDeCampos] = []
        for i, (titulo, exemplos) in enumerate(CATEGORIAS):
            grupo = GrupoDeCampos(titulo, exemplos)
            grade.addWidget(grupo, i // 2, i % 2, alignment=Qt.AlignmentFlag.AlignTop)
            self.grupos.append(grupo)
        cartao.corpo.addLayout(grade)
        return cartao

    def _montar_rodape(self) -> QWidget:
        rodape = QFrame()
        rodape.setObjectName("rodape")
        layout = QHBoxLayout(rodape)
        layout.setContentsMargins(24, 12, 24, 12)
        layout.setSpacing(8)

        esquerda = QVBoxLayout()
        esquerda.setSpacing(6)
        self.status = _rotulo(AVISO_CURTO, "secundario")
        esquerda.addWidget(self.status)
        self.progresso = QProgressBar()
        self.progresso.setRange(0, 1000)
        self.progresso.setTextVisible(False)
        self.progresso.hide()
        esquerda.addWidget(self.progresso)
        layout.addLayout(esquerda, stretch=1)
        layout.addSpacing(16)

        self.botao_erros = QPushButton("Ver erros")
        self.botao_erros.clicked.connect(self.mostrar_erros)
        self.botao_erros.hide()
        layout.addWidget(self.botao_erros)
        self.botao_abrir = QPushButton("Abrir pasta")
        self.botao_abrir.clicked.connect(self.abrir_pasta)
        self.botao_abrir.hide()
        layout.addWidget(self.botao_abrir)
        self.botao = QPushButton("Anonimizar")
        self.botao.setObjectName("primario")
        self.botao.setCursor(Qt.CursorShape.PointingHandCursor)
        self.botao.clicked.connect(self.iniciar)
        layout.addWidget(self.botao)
        return rodape

    # ---------- Tema ----------

    def aplicar_tema(self) -> None:
        escuro = self.tema_escuro.isChecked()
        app = QApplication.instance()
        # Também deixa a barra de título e os diálogos do sistema no mesmo tema
        app.styleHints().setColorScheme(Qt.ColorScheme.Dark if escuro else Qt.ColorScheme.Light)
        app.setStyleSheet(ESTILO.format(**TEMAS["escuro" if escuro else "claro"]))

    # ---------- Arquivos ----------

    def _mostrar_arquivos(self) -> None:
        layout = self.zona.layout_
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.arquivos:
            vazio = _rotulo("Arraste PDFs para cá ou clique em Adicionar PDFs…", "secundario")
            vazio.setAlignment(Qt.AlignmentFlag.AlignCenter)
            vazio.setMinimumHeight(56)
            layout.addWidget(vazio)
            return

        for arquivo in self.arquivos:
            linha = QWidget()
            linha_layout = QHBoxLayout(linha)
            linha_layout.setContentsMargins(0, 0, 0, 0)
            linha_layout.setSpacing(8)
            linha_layout.addWidget(QLabel("📄"))
            linha_layout.addWidget(QLabel(arquivo.name))
            linha_layout.addWidget(_rotulo(_tamanho_legivel(arquivo), "dica"))
            linha_layout.addStretch()
            linha_layout.addWidget(_botao_remover(lambda _=False, a=arquivo: self.remover_arquivo(a)))
            linha.setToolTip(str(arquivo))
            layout.addWidget(linha)

    def selecionar(self) -> None:
        caminhos, _ = QFileDialog.getOpenFileNames(self, "Selecionar PDFs", "", "PDF (*.pdf)")
        self.adicionar_arquivos([Path(c) for c in caminhos])

    def adicionar_arquivos(self, novos: list[Path]) -> None:
        if not novos:
            return
        # Acumula com a seleção anterior, sem repetir arquivos
        self.arquivos = list(dict.fromkeys(self.arquivos + novos))
        self._mostrar_arquivos()

    def remover_arquivo(self, arquivo: Path) -> None:
        self.arquivos.remove(arquivo)
        self._mostrar_arquivos()

    def _mostrar_pasta(self) -> None:
        if self.pasta_saida is None:
            self.rotulo_pasta.setText("Mesma pasta dos PDFs originais")
        else:
            self.rotulo_pasta.setText(str(self.pasta_saida))
        self.botao_pasta_original.setVisible(self.pasta_saida is not None)

    def selecionar_pasta(self) -> None:
        pasta = QFileDialog.getExistingDirectory(self, "Selecionar pasta de saída")
        if not pasta:
            return
        self.pasta_saida = Path(pasta)
        self._mostrar_pasta()

    def usar_pasta_original(self) -> None:
        self.pasta_saida = None
        self._mostrar_pasta()

    # ---------- Ajuda e resultado ----------

    def mostrar_ajuda(self) -> None:
        QMessageBox.information(self, "Como a busca funciona", AJUDA)

    def mostrar_erros(self) -> None:
        QMessageBox.warning(self, "Arquivos com erro", "\n".join(self.erros))

    def abrir_pasta(self) -> None:
        if self.pasta_resultado is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.pasta_resultado)))

    def _mostrar_status(self, texto: str, estado: str = "") -> None:
        self.status.setText(texto)
        self.status.setProperty("estado", estado)
        self.status.setObjectName("status" if estado else "secundario")
        _repolir(self.status)

    # ---------- Processamento ----------

    def coletar_termos(self) -> list[str]:
        # Junta os dados de todos os campos, sem repetições e mantendo a ordem
        termos = [valor for grupo in self.grupos for valor in grupo.valores()]
        return list(dict.fromkeys(termos))

    def _travar(self, travado: bool) -> None:
        for botao in (self.botao, self.botao_pdfs, self.botao_pasta):
            botao.setEnabled(not travado)

    def iniciar(self) -> None:
        termos = self.coletar_termos()

        if not self.arquivos:
            QMessageBox.warning(self, "Atenção", "Adicione pelo menos um PDF.")
            return
        if not termos:
            QMessageBox.warning(self, "Atenção", "Preencha pelo menos um dado a ocultar.")
            return

        self._travar(True)
        self.botao_abrir.hide()
        self.botao_erros.hide()
        self._mostrar_status("Preparando…")
        self.progresso.setValue(0)
        self.progresso.show()

        self.trabalho = Processamento(list(self.arquivos), termos, self.pasta_saida)
        self.trabalho.status.connect(self._mostrar_status)
        self.trabalho.progresso.connect(lambda valor: self.progresso.setValue(round(valor * 10)))
        self.trabalho.fim.connect(self.finalizar)
        self.trabalho.start()

    def finalizar(self, n: int, erros: list[str], destino: Path) -> None:
        self._travar(False)
        self.progresso.hide()
        self.erros = erros
        self.pasta_resultado = destino

        concluidos = n - len(erros)
        if erros:
            self._mostrar_status(f"⚠  {concluidos} de {n} arquivo(s) anonimizado(s). {len(erros)} falharam.", "erro")
            self.botao_erros.show()
        else:
            self._mostrar_status(
                f"✓  {concluidos} arquivo(s) anonimizado(s) com o sufixo {SUFIXO}. Revise antes de compartilhar.",
                "sucesso",
            )
        self.botao_abrir.setVisible(concluidos > 0)

def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))

    janela = Janela()
    # Ocupa no máximo a área livre da tela (sem a barra de tarefas)
    livre = app.primaryScreen().availableGeometry()
    janela.resize(min(960, livre.width() - 40), min(820, livre.height() - 60))
    janela.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
