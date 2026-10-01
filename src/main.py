from pathlib import Path
import os
import sys
import fitz
import pytesseract
import pandas as pd

from PIL import Image
from io import BytesIO


# Pasta raiz do projeto
PASTA_PROJETO = Path(__file__).resolve().parent.parent

# Tesseract local
CAMINHO_TESSERACT = os.path.join(
    PASTA_PROJETO,
    "tesseract",
    "tesseract.exe"
)

pytesseract.pytesseract.tesseract_cmd = CAMINHO_TESSERACT


def processar_pdf(caminho_pdf):
    print(f"Processando: {caminho_pdf}")

    pdf = fitz.open(caminho_pdf)

    dados = []

    for numero_pagina, pagina in enumerate(pdf, start=1):

        print(f"  Página {numero_pagina}")

        matriz = fitz.Matrix(2, 2)
        pix = pagina.get_pixmap(matrix=matriz)

        imagem = Image.open(
            BytesIO(pix.tobytes("png"))
        )

        texto = pytesseract.image_to_string(
            imagem,
            lang="por"
        )

        for linha in texto.splitlines():

            linha = linha.strip()

            if linha:
                dados.append({
                    "Página": numero_pagina,
                    "Texto": linha
                })

    pdf.close()

    return dados


def main():

    if len(sys.argv) < 2:
        print('Uso: python src/main.py "pasta"')
        sys.exit(1)

    pasta = Path(sys.argv[1])

    if not pasta.exists():
        print(f"Pasta não encontrada: {pasta}")
        sys.exit(1)

    if not pasta.is_dir():
        print(f"O caminho informado não é uma pasta: {pasta}")
        sys.exit(1)

    # Procura PDFs na pasta
    arquivos_pdf = list(pasta.glob("*.pdf"))

    if not arquivos_pdf:
        print("Nenhum PDF encontrado.")
        sys.exit(0)

    todos_dados = []

    for pdf in arquivos_pdf:
        dados = processar_pdf(pdf)
        todos_dados.extend(dados)

    # Excel de saída
    caminho_excel = pasta / "resultado.xlsx"

    df = pd.DataFrame(todos_dados)

    df.to_excel(
        caminho_excel,
        index=False
    )

    print()
    print(f"Concluído!")
    print(f"Excel: {caminho_excel}")


if __name__ == "__main__":
    main()