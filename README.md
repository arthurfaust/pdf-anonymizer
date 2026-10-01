# pdf-anonymizer

Ferramenta em Python para ocultar dados pessoais em arquivos PDF, como nomes, endereços e números de conta ou cartão. Funciona tanto em PDFs com texto quanto em PDFs escaneados ou gerados como imagem, usando OCR para localizar os dados.

O resultado é um novo PDF com tarjas pretas sobre os dados informados. O conteúdo por baixo das tarjas é removido de fato, inclusive os pixels das imagens, e os metadados do arquivo são limpos.

## Como funciona

Para cada página do documento:

1. **Detecção.** Se a página não tem texto ou contém imagens, ela passa pelo OCR.
2. **OCR.** A página é renderizada como imagem em alta resolução, convertida para preto e branco (binarização, que elimina destaques e fundos coloridos) e lida pelo Tesseract no modo de texto esparso. O resultado é uma lista de palavras com a posição de cada uma na página.
3. **Busca.** Cada termo é procurado na camada de texto do PDF e na lista de palavras do OCR. A comparação ignora acentos, pontuação e diferenças entre maiúsculas e minúsculas, e palavras coladas por pontuação (como `ORIG:ARTHUR`) são separadas antes da busca.
4. **Redação.** Cada ocorrência recebe uma tarja preta. Ao aplicar as redações, o texto e os pixels de imagem sob as tarjas são apagados.

Ao final, o documento passa por uma limpeza (`scrub`) que remove metadados, anexos, links e outros lugares onde dados podem ficar escondidos, e é salvo sem objetos órfãos do conteúdo original.

## Requisitos

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

Por padrão, o projeto procura o Tesseract em `C:\Program Files\Tesseract-OCR\tesseract.exe`. Se ele estiver instalado em outro lugar, informe o caminho num arquivo `.env` na raiz do projeto:

```
TESSERACT_CMD=C:\caminho\para\tesseract.exe
```

E rode passando o arquivo:

```powershell
uv run --env-file .env pdf-anonymizer
```

## Uso

O arquivo de entrada e a lista de termos a ocultar são definidos em `src/pdf_anonymizer/main.py`. Depois de ajustá-los, rode:

```powershell
uv run pdf-anonymizer
```

O PDF censurado é salvo no caminho de saída informado para `censurar_dados`.

### Dicas para escolher os termos

- **Informe as partes do nome separadamente** (`"ELIANA"`, `"SILVA"`), além do nome completo. Assim, ocorrências parciais ou abreviadas também são ocultadas.
- **Inclua identificadores indiretos**, como números de referência de transações, números de cliente e códigos postais, que permitem rastrear a pessoa.
- **Evite termos muito curtos ou genéricos.** Um termo como `"0683"` oculta qualquer ocorrência desse número no documento, inclusive em valores e datas.

## Parâmetros do OCR

A função `ocr_palavras` aceita ajustes para documentos difíceis:

| Parâmetro | Padrão | Descrição |
|---|---|---|
| `dpi` | `400` | Resolução da renderização. Valores maiores reconhecem melhor letras pequenas, mas são mais lentos. |
| `limite` | `170` | Tom de cinza (0 a 255) acima do qual o pixel vira branco na binarização. Aumente se o texto estiver sumindo; diminua se fundos ou destaques ainda atrapalharem. |
| `psm` | `11` | Modo de segmentação do Tesseract. O modo 11 (texto esparso) lida melhor com layouts irregulares, como endereços ao lado de códigos de barras. |
| `margem` | `1.5` | Folga, em pontos, adicionada às laterais das tarjas de palavras separadas por pontuação. |

## Estrutura do projeto

```
pdf-anonymizer/
├── data/                  # PDFs de entrada e saída (não versionado)
├── scripts/               # Scripts de teste e exploração
├── src/
│   └── pdf_anonymizer/
│       ├── __init__.py
│       ├── anonymizer.py  # OCR, busca e redação
│       └── main.py        # Ponto de entrada da linha de comando
├── pyproject.toml
└── README.md
```

## Limitações

- **O OCR pode errar.** Um caractere lido incorretamente, como `0` no lugar de `O` ou um dígito trocado, faz o termo não ser encontrado. **Revise manualmente o PDF gerado antes de compartilhá-lo.**
- **O OCR é lento.** Cada página escaneada leva alguns segundos para ser processada.
- **Apenas os termos informados são ocultados.** A ferramenta não detecta dados pessoais automaticamente.

## Privacidade

Os documentos processados por esta ferramenta costumam conter dados sensíveis. Mantenha a pasta `data/` e o arquivo `.env` no `.gitignore` para que nunca sejam enviados ao repositório.
