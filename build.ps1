$ErrorActionPreference = 'Stop'
$originalPath = $env:PATH
Push-Location $PSScriptRoot
try {
    if (!(Test-Path '.venv/Scripts/python.exe')) {
        throw 'Ambiente virtual ausente. Execute uv sync --group dev antes de gerar o executável.'
    }
    if (!(Test-Path 'vendor/tesseract/tessdata/por.traineddata')) {
        throw 'Copie o Tesseract com o idioma português para vendor/tesseract.'
    }

    # Evita incluir DLLs incompatíveis de outras ferramentas presentes no PATH.
    $env:PATH = "$PSScriptRoot\.venv\Scripts;$env:SystemRoot\System32;$env:SystemRoot"
    & '.venv/Scripts/python.exe' -m PyInstaller 'PDF Anonymizer.spec' --clean --noconfirm
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller falhou com código $LASTEXITCODE."
    }
}
finally {
    $env:PATH = $originalPath
    Pop-Location
}
