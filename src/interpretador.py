import re
from pathlib import Path


def interpretar_resultado(caminho_txt: Path) -> Path:
    caminho_txt = Path(caminho_txt)

    if not caminho_txt.exists():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {caminho_txt}"
        )

    termos_excluir = [
        "SECRET",
        "PREFEITURA",
        "C.",
        "Prezad",
        "Assunto:",
        "Destino:",
        "Três",
        "Origem",
        "Assinado",
        "Atenci",
        "COMUNIC",
        "RECEBID",
        "HORÁRIO",
        "Tel.",
        "PMTC",
        "Date",
    ]

    termos_corte = [
        "Faxineira",
        "Agente",
        "Auxiliar",
        "Técnico",
        "Farmacêutico",
        "Assessor",
        "Psicóloga",
        "Motorista",
        "Enfermeira",
    ]

    texto = caminho_txt.read_text(encoding="utf-8-sig")
    linhas_resultado = []

    for linha in texto.splitlines():

        if any(
            termo.casefold() in linha.casefold()
            for termo in termos_excluir
        ):
            continue

        correspondencia = re.match(
            r"^\s*(\d+)\s*[|]?\s*(.*)$",
            linha,
        )

        if not correspondencia:
            continue

        numero = correspondencia.group(1)
        texto_linha = correspondencia.group(2)

        # Corta o texto a partir da primeira palavra encontrada.
        padrao_corte = (
            r"\b(?:"
            + "|".join(re.escape(termo) for termo in termos_corte)
            + r")\b"
        )

        texto_linha = re.split(
            padrao_corte,
            texto_linha,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]

        # Remove caracteres especiais, mantendo letras e espaços.
        texto_linha = re.sub(
            r"[^A-Za-zÀ-ÖØ-öø-ÿ\s]",
            "",
            texto_linha,
        )

        texto_linha = re.sub(
            r"\s+",
            " ",
            texto_linha,
        ).strip()

        if texto_linha:
            linhas_resultado.append(
                f"{numero}\t{texto_linha}"
            )

    caminho_saida = caminho_txt.with_name(
        f"{caminho_txt.stem}_limpo.txt"
    )

    caminho_saida.write_text(
        "\n".join(linhas_resultado),
        encoding="utf-8",
    )

    return caminho_saida
