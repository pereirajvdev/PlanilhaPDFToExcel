from pathlib import Path
import os
import re
import sys
import fitz
import pytesseract
import pandas as pd

from PIL import Image
from io import BytesIO


# ============================================================
# CONFIGURAÇÃO
# ============================================================

PASTA_PROJETO = Path(__file__).resolve().parent.parent

ARQUIVO_INPUT = PASTA_PROJETO / "data" / "input.txt"

CAMINHO_TESSERACT = (
    PASTA_PROJETO / "tesseract" / "tesseract.exe"
)

pytesseract.pytesseract.tesseract_cmd = str(
    CAMINHO_TESSERACT
)


# ============================================================
# PROCESSAMENTO DE PDF EXISTENTE
# ============================================================

def processar_pdf(caminho_pdf):
    print(f"Processando: {caminho_pdf}")

    pdf = fitz.open(caminho_pdf)
    dados = []

    try:
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
                    numeros, letras = separar_numeros_letras(
                        linha
                    )

                    dados.append({
                        "Números": numeros,
                        "Letras": letras
                    })

    finally:
        pdf.close()

    return dados


def adicionar_espacos_caracteres_especiais(texto):
    texto = re.sub(
        r"([^A-Za-zÀ-ÿ0-9\s])",
        r" \1 ",
        texto
    )

    texto = re.sub(r"\s+", " ", texto)

    return texto.strip()


def remover_caracteres_especiais(texto):
    return re.sub(
        r"[^A-Za-zÀ-ÿ0-9\s]",
        "",
        texto
    )


def separar_numeros_letras(texto):
    texto = adicionar_espacos_caracteres_especiais(
        texto
    )

    texto = remover_caracteres_especiais(texto)

    partes = texto.split()

    numeros = []
    letras = []

    for parte in partes:
        if any(caractere.isdigit() for caractere in parte):
            numeros.append(parte)
        else:
            letras.append(parte)

    return " ".join(numeros), " ".join(letras)


# ============================================================
# MODO INPUT: EXTRAÇÃO DE MATRÍCULAS E SERVIDORES
# ============================================================

def eh_matricula(linha):
    """
    Identifica linhas que contêm somente uma matrícula.
    Aceita matrículas numéricas e matrículas com uma letra,
    como 3072S.
    """
    return bool(
        re.fullmatch(r"\d{3,6}[A-Za-z]?", linha.strip())
    )


def parece_nome(linha):
    """
    Filtra cabeçalhos, cargos e outros textos que não
    aparentam ser nomes de servidores.
    """
    linha = re.sub(r"\s+", " ", linha).strip()

    if not linha or eh_matricula(linha):
        return False

    texto = linha.upper()

    termos_ignorar = [
        "PREFEITURA",
        "SECRETARIA",
        "COMUNICAÇÃO INTERNA",
        "COMUNICACAO INTERNA",
        "C.I.",
        "TRÊS CORAÇÕES",
        "TRES CORACOES",
        "MATRÍCULA",
        "MATRICULA",
        "SERVIDOR",
        "CARGO",
        "OBSERVAÇÃO",
        "OBSERVACAO",
        "ABONO PECUNIÁRIO",
        "ABONO PECUNIARIO",
        "ATENCIOSAMENTE",
        "ASSUNTO:",
        "ORIGEM:",
        "DESTINO:",
        "SECRETÁRIA",
        "SECRETARIO",
        "SECRETÁRIO",
        "HORÁRIO",
        "HORARIO",
        "RECEBEM",
        "VIA SEDESO",
        "DESENVOLVIMENTO SOCIAL",
        "PSF ",
        "ESF ",
        "CEO",
        "CER IV",
        "VIGILÂNCIA",
        "VIGILANCIA",
        "AGENTE DE ",
        "TÉCNICO EM ",
        "TECNICO EM ",
        "AUXILIAR DE ",
        "ENFERMEIRA",
        "FARMACÊUTICO",
        "FARMACEUTICO",
        "PSICÓLOGA",
        "PSICOLOGA",
        "ASSESSOR SETORIAL",
    ]

    if any(termo in texto for termo in termos_ignorar):
        return False

    # Elimina linhas sem letras.
    if not re.search(r"[A-Za-zÀ-ÿ]", linha):
        return False

    # Um nome costuma ter pelo menos duas palavras.
    if len(linha.split()) < 2:
        return False

    # Evita incorporar parágrafos inteiros.
    if len(linha) > 65:
        return False

    return True


def extrair_matriculas_servidores(texto):
    """
    Extrai pares de matrícula e servidor de um texto OCR.

    Trata:
    - Blocos de matrículas seguidos de nomes.
    - Matrícula seguida diretamente pelo nome.
    - Documentos diferentes no mesmo arquivo de texto.

    A associação é feita pela ordem em que os dados aparecem.
    """
    linhas = [
        re.sub(r"\s+", " ", linha).strip()
        for linha in texto.splitlines()
        if linha.strip()
    ]

    resultados = []
    matriculas_processadas = set()
    i = 0

    while i < len(linhas):
        if not eh_matricula(linhas[i]):
            i += 1
            continue

        # Captura o bloco consecutivo de matrículas.
        matriculas = []

        while i < len(linhas) and eh_matricula(linhas[i]):
            matriculas.append(linhas[i])
            i += 1

        nomes = []

        # Procura os nomes depois das matrículas.
        while i < len(linhas):
            linha = linhas[i]
            texto_upper = linha.upper()

            # Outro bloco de matrículas.
            if eh_matricula(linha):
                break

            # Cabeçalhos que encerram a lista de nomes.
            if any(
                termo in texto_upper
                for termo in [
                    "PREFEITURA MUNICIPAL",
                    "COMUNICAÇÃO INTERNA",
                    "COMUNICACAO INTERNA",
                    "ABONO PECUNIÁRIO",
                    "ABONO PECUNIARIO",
                ]
            ):
                break

            # Quando a tabela apresenta os cargos, não
            # devemos continuar capturando nomes.
            if texto_upper in {
                "CARGO",
                "SERVIDOR",
                "MATRÍCULA",
                "MATRICULA",
                "OBSERVAÇÃO",
                "OBSERVACAO",
            }:
                break

            if parece_nome(linha):
                nomes.append(linha)

                # No formato de tabela com matrícula e nome
                # intercalados, normalmente há apenas um
                # nome para cada matrícula.
                if len(matriculas) == 1:
                    break

            i += 1

        # Relaciona matrícula e nome pela posição.
        if len(matriculas) != len(nomes):
            print(
                "Aviso: quantidade divergente no bloco "
                f"de matrículas: {len(matriculas)}; "
                f"nomes identificados: {len(nomes)}."
            )

        for matricula, servidor in zip(matriculas, nomes):
            chave = matricula.strip()

            # Evita duplicar a mesma matrícula.
            if chave in matriculas_processadas:
                continue

            matriculas_processadas.add(chave)

            resultados.append({
                "matricula": matricula,
                "servidor": servidor
            })

    return pd.DataFrame(
        resultados,
        columns=["matricula", "servidor"]
    )


def processar_input(pasta_saida):
    """
    Lê data/input.txt e gera resultado.xlsx na pasta informada.
    """
    if not ARQUIVO_INPUT.exists():
        print(f"Arquivo de entrada não encontrado: {ARQUIVO_INPUT}")
        sys.exit(1)

    print(f"Lendo: {ARQUIVO_INPUT}")

    texto = ARQUIVO_INPUT.read_text(encoding="utf-8-sig")

    df = extrair_matriculas_servidores(texto)

    if df.empty:
        print("Nenhuma matrícula e servidor foram encontrados.")
        sys.exit(1)

    caminho_excel = pasta_saida / "resultado.xlsx"

    df.to_excel(caminho_excel, index=False)

    print()
    print(f"Servidores encontrados: {len(df)}")
    print(f"Excel gerado: {caminho_excel}")


def processar_pdf_texto(caminho_pdf):
    print(f"Processando OCR: {caminho_pdf}")

    pdf = fitz.open(caminho_pdf)
    textos = []

    try:
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

            textos.append(
                f"--- Página {numero_pagina} ---\n{texto}"
            )

    finally:
        pdf.close()

    return "\n".join(textos)


def processar_modo_texto(pasta):
    arquivos_pdf = sorted(pasta.glob("*.pdf"))

    if not arquivos_pdf:
        print("Nenhum PDF encontrado.")
        sys.exit(0)

    textos = []

    for pdf in arquivos_pdf:
        texto = processar_pdf_texto(pdf)

        textos.append(
            f"{'=' * 70}\n"
            f"ARQUIVO: {pdf.name}\n"
            f"{'=' * 70}\n\n"
            f"{texto}"
        )

    caminho_txt = pasta / "resultado.txt"

    caminho_txt.write_text(
        "\n\n".join(textos),
        encoding="utf-8"
    )

    print()
    print("OCR concluído!")
    print(f"Arquivo TXT: {caminho_txt}")


# ============================================================
# EXECUÇÃO PRINCIPAL
# ============================================================


def main():
    argumentos = sys.argv[1:]

    if not argumentos:
        print(
            'Uso:\n'
            '  python src/main.py "pasta"\n'
            '  python src/main.py "pasta" --input\n'
            '  python src/main.py "pasta" --texto\n'
            '  python src/main.py "arquivo.txt" --interpretar'
        )
        sys.exit(1)

    modo_input = "--input" in argumentos
    modo_texto = "--texto" in argumentos
    modo_interpretar = "--interpretar" in argumentos

    modos = [
        modo_input,
        modo_texto,
        modo_interpretar,
    ]

    if sum(modos) > 1:
        print("Informe apenas um modo por execução.")
        sys.exit(1)

    argumentos_caminho = [
        argumento
        for argumento in argumentos
        if argumento not in ("--input", "--texto", "--interpretar")
    ]

    if not argumentos_caminho:
        print("Informe o caminho do arquivo ou da pasta.")
        sys.exit(1)

    caminho = Path(argumentos_caminho[0])

    # Interpreta um arquivo TXT e gera outro TXT.
    if modo_interpretar:
        if not caminho.exists():
            print(f"Arquivo não encontrado: {caminho}")
            sys.exit(1)

        if not caminho.is_file() or caminho.suffix.lower() != ".txt":
            print("O modo --interpretar exige o caminho de um arquivo .txt.")
            sys.exit(1)

        from interpretador import interpretar_resultado

        caminho_saida = interpretar_resultado(caminho)

        print(f"Resultado salvo em: {caminho_saida}")
        return

    # Os outros modos exigem uma pasta.
    if not caminho.exists():
        print(f"Pasta não encontrada: {caminho}")
        sys.exit(1)

    if not caminho.is_dir():
        print(f"O caminho informado não é uma pasta: {caminho}")
        sys.exit(1)

    # Apenas OCR e saída em TXT.
    if modo_texto:
        processar_modo_texto(caminho)
        return

    # Processamento a partir do data/input.txt.
    if modo_input:
        processar_input(caminho)
        return

    # Processamento normal dos PDFs.
    arquivos_pdf = list(caminho.glob("*.pdf"))

    if not arquivos_pdf:
        print("Nenhum PDF encontrado.")
        sys.exit(0)

    todos_dados = []

    for pdf in arquivos_pdf:
        dados = processar_pdf(pdf)
        todos_dados.extend(dados)

    caminho_excel = caminho / "resultado.xlsx"

    df = pd.DataFrame(todos_dados)
    df.to_excel(caminho_excel, index=False)

    from openpyxl import load_workbook

    wb = load_workbook(caminho_excel)
    ws = wb.active
    ws.insert_rows(2)
    wb.save(caminho_excel)

    print()
    print("Concluído!")
    print(f"Excel: {caminho_excel}")


if __name__ == "__main__":
    main()
