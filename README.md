# pdf-anonymizer

Ferramenta em Python com interface gráfica para ocultar dados pessoais em arquivos PDF, como nomes, endereços e números de conta ou cartão. Funciona em PDFs com texto, em PDFs escaneados ou gerados como imagem e em PDFs cujo texto foi desenhado como vetores, usando OCR para localizar os dados quando a camada de texto não é suficiente.

O resultado é um novo PDF com tarjas pretas sobre os dados informados. O conteúdo por baixo das tarjas é removido de fato, inclusive os pixels das imagens e os desenhos vetoriais atingidos, e os metadados do arquivo são limpos.

## Como funciona

Para cada página do documento:

1. **Extração do texto nativo.** As palavras da camada de texto do PDF são extraídas caractere a caractere, junto com a posição de cada uma na página. Espaços e pontuação separam as palavras, de modo que trechos colados como `ORIG:ARTHUR` viram duas palavras.

2. **Detecção.** A página passa pelo OCR se não tiver texto nativo, se contiver imagens ou se tiver muitos glifos desenhados como vetores (30 ou mais formas preenchidas com curvas que não estão sobre texto nativo), situação comum em PDFs gerados pelo iOS/Quartz.

3. **OCR.** A página é renderizada em tons de cinza em alta resolução, convertida para preto e branco (binarização, que elimina destaques e fundos coloridos) e lida pelo Tesseract no modo de texto esparso. Cada palavra reconhecida é dividida nas partes alfanuméricas, e cada parte recebe uma área proporcional dentro da caixa da palavra, com uma pequena folga nas laterais.

4. **Busca.** Cada termo é procurado na camada de texto nativa e, quando houve OCR, também nas palavras reconhecidas. A comparação ignora acentos, pontuação, espaços e diferenças entre maiúsculas e minúsculas, e trata como iguais caracteres que o OCR costuma confundir (`B` e `8`, `O` e `0`, `I`, `L` e `1`). Um termo pode corresponder a várias palavras consecutivas, então `123.456.789-00` é encontrado mesmo que o documento o divida em partes. Só palavras inteiras são encontradas: `SILVA` não corresponde a `SILVEIRA`.

5. **Redação.** Cada ocorrência recebe uma tarja preta. Ao aplicar as redações, o texto, os pixels de imagem e os desenhos vetoriais que tocam as tarjas são apagados.

Ao final, o documento passa por uma limpeza (`scrub`) que remove metadados, anexos, links e outros lugares onde dados podem ficar escondidos, e é salvo sem objetos órfãos do conteúdo original e com os streams comprimidos.

## Para quem vai só usar o programa

Se você recebeu o programa já empacotado (um arquivo `.zip` com a pasta `PDF Anonymizer`), não precisa instalar Python, uv nem Tesseract:

1. Extraia o `.zip` para uma pasta do computador.
2. Abra o arquivo `PDF Anonymizer.exe` que está dentro dela. Não tire o `.exe` da pasta, porque ele depende da pasta `_internal` que fica ao lado.
3. Na primeira vez, o Windows pode mostrar o aviso "O Windows protegeu o computador". Clique em **Mais informações** e depois em **Executar assim mesmo**.

O modo de usar a janela está descrito em [Uso](#uso). O restante deste documento é voltado a quem desenvolve o projeto.

## Requisitos para desenvolvimento

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

O local do Tesseract é definido no início de `src/pdf_anonymizer/anonymizer.py`, pela função `_pasta_tesseract`:

- **Rodando pelo código-fonte**, o projeto usa a instalação padrão em `C:\Program Files\Tesseract-OCR`. Se o Tesseract estiver instalado em outro lugar, altere o caminho nessa função.
- **Rodando pelo executável**, o projeto usa a cópia do Tesseract que vai empacotada junto com o programa (veja [Gerando o executável](#gerando-o-executável)).

Nos dois casos, a variável de ambiente `TESSDATA_PREFIX` é apontada para a pasta `tessdata` correspondente.

## Uso

Abra a interface pelo código-fonte:

```powershell
uv run pdf-anonymizer
```

Ou abra o `PDF Anonymizer.exe`, se estiver usando o executável.

Na janela:

1. Clique em **Selecionar PDFs...** e escolha um ou mais arquivos.

2. Opcionalmente, clique em **Selecionar pasta de saída...** para escolher onde os arquivos censurados serão salvos. Se nenhuma pasta for escolhida, eles são salvos na mesma pasta dos originais.

3. Preencha os dados a ocultar nos campos de cada categoria: nome, sobrenome, contato, identificador, conta ou cartão, endereço e outros dados. Os textos em cinza dentro dos campos são apenas exemplos e não são usados.

4. Use o botão **+** ao lado de um campo para criar outro campo logo abaixo, na mesma categoria. Campos vazios são ignorados.

5. Clique em **Anonimizar** e acompanhe o andamento pela barra de progresso.

As categorias servem apenas para organizar o preenchimento. Todos os dados preenchidos são reunidos em uma única lista, sem repetições, e procurados da mesma forma em todo o documento.

Cada arquivo censurado recebe o sufixo `_censurado` (por exemplo, `extrato.pdf` gera `extrato_censurado.pdf`). Se já existir um arquivo com esse nome no destino, ele é substituído. Atenção: se você escolher uma pasta de saída e selecionar dois PDFs com o mesmo nome vindos de pastas diferentes, o segundo substitui o primeiro.

O processamento roda em segundo plano, então a janela continua respondendo durante o OCR. Se um arquivo falhar, os demais continuam sendo processados, e os erros são listados na mensagem final.

### Uso como biblioteca

As funções de `anonymizer.py` também podem ser usadas diretamente:

```python
from pdf_anonymizer.anonymizer import abrir_arquivo, censurar_dados

doc = abrir_arquivo("extrato.pdf")
censurar_dados(doc, ["Arthur", "Faust", "123.456.789-00"], "extrato_censurado.pdf")
doc.close()
```

`censurar_dados` aceita ainda `log`, uma função que recebe as mensagens de andamento (por padrão, `print`), e `ao_avancar`, uma função chamada ao fim de cada página com a página atual e o total.

### Dicas para escolher os termos

- **Informe as partes do nome separadamente** (`ARTHUR`, `SILVA`), além do nome completo. Um termo só é encontrado quando aparece inteiro e com as palavras na mesma ordem, então `ARTHUR SILVA` não oculta um `SILVA` isolado nem `A. SILVA`.

- **Não é preciso repetir variações de pontuação ou de maiúsculas.** `12345678900` já encontra `123.456.789-00`, e `jose` já encontra `JOSÉ`.

- **Inclua identificadores indiretos**, como números de referência de transações, números de cliente e códigos postais, que permitem rastrear a pessoa.

- **Evite termos muito curtos ou genéricos.** Um termo como `0683` oculta qualquer ocorrência desse número no documento, inclusive em valores e datas, e um termo como `da` ocultaria todas as ocorrências dessa palavra. Lembre também que `O`, `I`, `L` e `B` são comparados como `0`, `1`, `1` e `8`, o que pode gerar ocorrências inesperadas em termos curtos.

## Gerando o executável

O executável é gerado com o [PyInstaller](https://pyinstaller.org/) e inclui uma cópia do Tesseract, para que quem for usar não precise instalar nada. Todos os comandos são executados na raiz do projeto.

**1. Copie o Tesseract para o projeto.** Crie a pasta `vendor\tesseract` e copie para ela todo o conteúdo de `C:\Program Files\Tesseract-OCR`. Para reduzir o tamanho, apague de `vendor\tesseract\tessdata` os arquivos `.traineddata` de outros idiomas, mantendo o `por.traineddata`. **Não apague as subpastas `configs` e `tessconfigs`**: o OCR depende delas.

**2. Instale o PyInstaller** como dependência de desenvolvimento:

```powershell
uv add --dev pyinstaller
```

**3. Gere o executável** a partir do arquivo de entrada `iniciar.py`:

```powershell
uv run pyinstaller iniciar.py --name "PDF Anonymizer" --windowed --onedir --paths src --add-data "vendor\tesseract;tesseract" --clean --noconfirm
```

O resultado fica em `dist\PDF Anonymizer\`. Nas próximas vezes, basta usar a receita salva no arquivo `.spec`:

```powershell
uv run pyinstaller "PDF Anonymizer.spec" --clean --noconfirm
```

O PyInstaller inclui apenas o código importado a partir de `iniciar.py` e os arquivos indicados com `--add-data`. As pastas `data/` e `scripts/` não entram no executável.

**4. Teste** o `PDF Anonymizer.exe` com um PDF de texto comum e com um PDF escaneado, para confirmar que o OCR funciona. O teste definitivo é em um computador sem Python e sem Tesseract instalados. Se o programa fechar sem mostrar nada, gere de novo sem a opção `--windowed` para ver a mensagem de erro no terminal.

**5. Distribua** compactando a pasta `dist\PDF Anonymizer` inteira em um `.zip`.

Como o executável não tem assinatura digital, o Windows SmartScreen e alguns antivírus podem desconfiar dele. Se a empresa tiver equipe de TI, vale pedir a liberação ou a assinatura do executável.

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
├── data/                  # PDFs de teste (não versionado, não entra no executável)
├── scripts/               # Scripts de teste e exploração (não entram no executável)
├── src/
│   └── pdf_anonymizer/
│       ├── __init__.py
│       ├── anonymizer.py  # Extração de texto, OCR, busca e redação
│       ├── new_gui.py     # Interface gráfica (Tkinter)
│       ├── gui.py         # Interface anterior, não usada pelo programa
│       └── main.py        # Ponto de entrada; abre a interface
├── vendor/
│   └── tesseract/         # Cópia do Tesseract para o executável (não versionado)
├── main.py                # Arquivo de entrada usado pelo PyInstaller
├── PDF Anonymizer.spec    # Receita do build do PyInstaller
├── pyproject.toml
├── uv.lock
└── README.md
```

As pastas `build/` e `dist/`, geradas pelo PyInstaller, também não são versionadas.

## Limitações

- **O OCR pode errar.** Um caractere lido incorretamente, como um dígito trocado, faz o termo não ser encontrado. A normalização cobre as confusões mais comuns (`O`/`0`, `I`/`L`/`1`, `B`/`8`), mas não todas. **Revise manualmente o PDF gerado antes de compartilhá-lo.**

- **As tarjas do OCR são aproximadas.** A posição de cada parte de uma palavra é estimada pela proporção de caracteres, por isso as tarjas têm uma folga lateral e podem cobrir um pouco do texto vizinho.

- **Desenhos vetoriais que tocam uma tarja são removidos**, inclusive linhas de tabelas e bordas que passem pela área censurada.

- **O OCR é lento.** Cada página que passa pelo OCR leva alguns segundos para ser processada.

- **Apenas os termos informados são ocultados.** A ferramenta não detecta dados pessoais automaticamente.

- **Apenas Windows.** O caminho do Tesseract e o executável gerado são específicos para Windows.

## Privacidade

Os documentos processados por esta ferramenta costumam conter dados sensíveis. Mantenha a pasta `data/` no `.gitignore` para que nunca seja enviada ao repositório. Se os arquivos censurados forem salvos na mesma pasta dos originais, cuidado para não compartilhar o original por engano. Escolher uma pasta de saída separada ajuda a evitar esse risco.

O processamento acontece inteiramente no computador de quem usa o programa. Nenhum documento é enviado para servidores externos.
