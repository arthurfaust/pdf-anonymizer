# pdf-anonymizer

Ferramenta em Python com interface gráfica para ocultar dados pessoais em arquivos PDF, como nomes, endereços e números de conta ou cartão. Funciona em PDFs com texto, em PDFs escaneados ou gerados como imagem e em PDFs cujo texto foi desenhado como vetores, usando OCR para localizar os dados quando a camada de texto não é suficiente.

O resultado é um novo PDF com tarjas pretas sobre os dados informados. O conteúdo por baixo das tarjas é removido de fato, inclusive os pixels das imagens e os desenhos vetoriais atingidos, e os metadados do arquivo são limpos.

## Como funciona

Para cada página do documento:

1. **Extração do texto nativo.** As palavras da camada de texto do PDF são extraídas caractere a caractere, junto com a posição de cada uma na página. Espaços e pontuação separam as palavras, de modo que trechos colados como `ORIG:ARTHUR` viram duas palavras.
2. **Detecção.** A página passa pelo OCR se não tiver texto nativo, se contiver imagens ou se tiver muitos glifos desenhados como vetores (30 ou mais formas preenchidas com curvas que não estão sobre texto nativo), situação comum em PDFs gerados pelo iOS/Quartz.
3. **OCR.** A página é renderizada em tons de cinza em alta resolução, convertida para preto e branco (binarização, que elimina destaques e fundos coloridos) e lida pelo Tesseract no modo de texto esparso. Cada palavra reconhecida é dividida nas partes alfanuméricas, e cada parte recebe uma área proporcional dentro da caixa da palavra, com uma pequena folga nas laterais.
4. **Busca.** Cada termo é procurado na camada de texto nativa e, quando houve OCR, também nas palavras reconhecidas. A comparação ignora acentos, pontuação, espaços e diferenças entre maiúsculas e minúsculas, e trata como iguais caracteres que o OCR costuma confundir (`B` e `8`, `O` e `0`, `I`, `L` e `1`). Um termo pode corresponder a várias palavras consecutivas, então `123.456.789-00` é encontrado mesmo que o documento o divida em partes.
5. **Redação.** Cada ocorrência recebe uma tarja preta. Ao aplicar as redações, o texto, os pixels de imagem e os desenhos vetoriais que tocam as tarjas são apagados.

Ao final, o documento passa por uma limpeza (`scrub`) que remove metadados, anexos, links e outros lugares onde dados podem ficar escondidos, e é salvo sem objetos órfãos do conteúdo original e com os streams comprimidos.

## Requisitos

- Windows (o caminho do Tesseract está definido para a instalação padrão no Windows; veja [Configuração](#configuração))
- [uv](https://docs.astral.sh/uv/)
- Python 3.14 ou superior (o uv instala automaticamente, se necessário)
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) com o pacote de idioma português (`por`)

O Tesseract é um programa nativo e precisa ser instalado à parte, fora do uv.

### Instalando o Tesseract no Windows

```powershell
winget install -e --id UB-Mannheim.TesseractOCR
```

Confira se o português está disponível:

```powershell
& "C:\Program Files\Tesseract-OCR\tesseract.exe" --list-langs
```

Se `por` não aparecer na lista, baixe o arquivo `por.traineddata` do repositório [tesseract-ocr/tessdata](https://github.com/tesseract-ocr/tessdata) e coloque na pasta `C:\Program Files\Tesseract-OCR\tessdata`.

## Instalação

```powershell
git clone <url-do-repositorio>
cd pdf-anonymizer
uv sync
```

## Configuração

O projeto procura o Tesseract em `C:\Program Files\Tesseract-OCR\tesseract.exe`. Esse caminho está fixo no início de `src/pdf_anonymizer/anonymizer.py`:

```python
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
```

Se o Tesseract estiver instalado em outro lugar, altere essa linha.

## Uso

Abra a interface:

```powershell
uv run pdf-anonymizer
```

Na janela:

1. Clique em **Selecionar PDFs...** e escolha um ou mais arquivos.
2. Digite os dados a ocultar no campo de texto, **um por linha**.
3. Clique em **Anonimizar** e acompanhe o andamento pela barra de progresso.

Cada arquivo censurado é salvo na mesma pasta do original, com o sufixo `_censurado` (por exemplo, `extrato.pdf` gera `extrato_censurado.pdf`). Se já existir um arquivo com esse nome, ele é substituído.

O processamento roda em segundo plano, então a janela continua respondendo durante o OCR. Se um arquivo falhar, os demais continuam sendo processados, e os erros são listados na mensagem final.

### Uso como biblioteca

As funções de `anonymizer.py` também podem ser usadas diretamente:

```python
from pdf_anonymizer.anonymizer import abrir_arquivo, censurar_dados

doc = abrir_arquivo("extrato.pdf")
censurar_dados(doc, ["ELIANA", "SILVA", "123.456.789-00"], "extrato_censurado.pdf")
doc.close()
```

`censurar_dados` aceita ainda `log`, uma função que recebe as mensagens de andamento (por padrão, `print`), e `ao_avancar`, uma função chamada ao fim de cada página com a página atual e o total.

### Dicas para escolher os termos

- **Informe as partes do nome separadamente** (`ELIANA`, `SILVA`), além do nome completo. Assim, ocorrências parciais ou abreviadas também são ocultadas.
- **Inclua identificadores indiretos**, como números de referência de transações, números de cliente e códigos postais, que permitem rastrear a pessoa.
- **Evite termos muito curtos ou genéricos.** Um termo como `0683` oculta qualquer ocorrência desse número no documento, inclusive em valores e datas. Lembre também que `O`, `I`, `L` e `B` são comparados como `0`, `1`, `1` e `8`, o que pode gerar ocorrências inesperadas em termos curtos.

## Parâmetros

### OCR

A função `ocr_palavras` aceita ajustes para documentos difíceis:

| Parâmetro | Padrão | Descrição |
|---|---|---|
| `dpi` | `400` | Resolução da renderização. Valores maiores reconhecem melhor letras pequenas, mas são mais lentos. |
| `limite` | `170` | Tom de cinza (0 a 255) acima do qual o pixel vira branco na binarização. Aumente se o texto estiver sumindo; diminua se fundos ou destaques ainda atrapalharem. |
| `psm` | `11` | Modo de segmentação do Tesseract. O modo 11 (texto esparso) lida melhor com layouts irregulares, como endereços ao lado de códigos de barras. |
| `margem` | `0.5` | Folga adicionada a cada lateral das tarjas do OCR, como fração da altura da palavra. Com `0.5`, uma palavra de 10 pt de altura ganha 5 pt de cada lado. |

### Detecção

| Função | Parâmetro | Padrão | Descrição |
|---|---|---|---|
| `precisa_ocr` | `min_glifos` | `30` | Quantidade de glifos vetoriais fora do texto nativo a partir da qual a página passa pelo OCR. |
| `contar_glifos_vetoriais` | `altura_max` | `40` | Altura máxima, em pontos, para um desenho ser considerado um glifo. Formas maiores, como logotipos e caixas, são ignoradas. |

## Estrutura do projeto

```
pdf-anonymizer/
├── data/                  # PDFs de entrada e saída (não versionado)
├── scripts/               # Scripts de teste e exploração
├── src/
│   └── pdf_anonymizer/
│       ├── __init__.py
│       ├── anonymizer.py  # Extração de texto, OCR, busca e redação
│       ├── gui.py         # Interface gráfica (Tkinter)
│       └── main.py        # Ponto de entrada; abre a interface
├── pyproject.toml
├── uv.lock
└── README.md
```

## Limitações

- **O OCR pode errar.** Um caractere lido incorretamente, como um dígito trocado, faz o termo não ser encontrado. A normalização cobre as confusões mais comuns (`O`/`0`, `I`/`L`/`1`, `B`/`8`), mas não todas. **Revise manualmente o PDF gerado antes de compartilhá-lo.**
- **As tarjas do OCR são aproximadas.** A posição de cada parte de uma palavra é estimada pela proporção de caracteres, por isso as tarjas têm uma folga lateral e podem cobrir um pouco do texto vizinho.
- **Desenhos vetoriais que tocam uma tarja são removidos**, inclusive linhas de tabelas e bordas que passem pela área censurada.
- **O OCR é lento.** Cada página que passa pelo OCR leva alguns segundos para ser processada.
- **Apenas os termos informados são ocultados.** A ferramenta não detecta dados pessoais automaticamente.

## Privacidade

Os documentos processados por esta ferramenta costumam conter dados sensíveis. Mantenha a pasta `data/` no `.gitignore` para que nunca seja enviada ao repositório. Como os arquivos censurados são salvos ao lado dos originais, cuidado para não compartilhar o original por engano.