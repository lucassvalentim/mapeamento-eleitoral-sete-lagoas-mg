import pandas as pd


def padronizar_chaves(df: pd.DataFrame, chaves: list[str]) -> pd.DataFrame:
    """Remove espaços em branco das colunas usadas como chave."""
    for col in chaves:
        df[col] = df[col].astype("string").str.strip()
    return df


def processar_votacao(
    caminho_arquivo: str,
    municipio: str,
    cargo: str,
    chaves: list[str]
) -> pd.DataFrame:
    """Lê, filtra, agrupa os votos e padroniza as chaves."""
    df_votacao = pd.read_csv(caminho_arquivo, sep=";", encoding="latin-1", dtype=str)

    df_filtrado = df_votacao[
        (df_votacao["NM_MUNICIPIO"].str.upper() == municipio) &
        (df_votacao["DS_CARGO"].str.upper() == cargo)
    ].copy()

    df_filtrado["QT_VOTOS"] = pd.to_numeric(
        df_filtrado["QT_VOTOS"], errors="coerce"
    ).fillna(0)

    colunas_grupo = chaves + ["NR_VOTAVEL", "NM_VOTAVEL"]
    df_agrupado = (
        df_filtrado
        .groupby(colunas_grupo, as_index=False)
        .agg({"QT_VOTOS": "sum"})
    )

    return padronizar_chaves(df_agrupado, chaves)


def processar_locais(caminho_arquivo: str, chaves: list[str]) -> pd.DataFrame:
    """Lê os locais de votação, seleciona colunas, limpa chaves e remove duplicatas."""
    df_locais = pd.read_csv(caminho_arquivo, sep=";", encoding="latin-1", dtype=str)

    colunas_localizacao = chaves + [
        "NR_LOCAL_VOTACAO",
        "NM_LOCAL_VOTACAO",
        "DS_ENDERECO",
        "NM_BAIRRO",
        "NR_LATITUDE",
        "NR_LONGITUDE"
    ]
    df_localizacao = df_locais[colunas_localizacao].copy()
    df_localizacao = padronizar_chaves(df_localizacao, chaves)
    df_localizacao = df_localizacao.drop_duplicates(subset=chaves)

    return df_localizacao


def cruzar_dados(
    df_votos: pd.DataFrame,
    df_localizacao: pd.DataFrame,
    chaves: list[str]
) -> pd.DataFrame:
    """Une votação com localização e converte latitude/longitude para numérico."""
    df_final = df_votos.merge(
        df_localizacao,
        on=chaves,
        how="left",
        validate="many_to_one"
    )

    for col in ["NR_LATITUDE", "NR_LONGITUDE"]:
        df_final[col] = pd.to_numeric(
            df_final[col].astype("string").str.replace(",", "."),
            errors="coerce"
        )

    return df_final


def salvar_csv(df: pd.DataFrame, caminho_saida: str) -> None:
    """Salva o DataFrame final em CSV no padrão brasileiro (separador ';')."""
    df.to_csv(caminho_saida, sep=";", index=False, encoding="utf-8-sig")
    print(f"Arquivo salvo com sucesso em: {caminho_saida}")


def main() -> None:
    # Caminhos dos arquivos
    path_votacao = './dados/brutos/votacao_secao_2026_BR/votacao_secao_2026_BR.csv'
    path_locais = './dados/brutos/eleitorado_local_votacao_2026/eleitorado_local_votacao_2026_MG.csv'
    path_saida = './dados/processados/votacao_geolocalizada.csv'

    # Parâmetros
    municipio_alvo = "SETE LAGOAS"
    cargo_alvo = "PRESIDENTE"
    chaves_merge = ["CD_MUNICIPIO", "NR_ZONA", "NR_SECAO", "NR_TURNO"]

    # Execução do pipeline
    print("------ Leitura do arquivo de votacao ------")
    df_votos = processar_votacao(path_votacao, municipio_alvo, cargo_alvo, chaves_merge)
    print("------ Leitura do arquivo do eleitorado ------")
    df_locais = processar_locais(path_locais, chaves_merge)
    print("------ Merge dos dados ------")
    df_dados_finais = cruzar_dados(df_votos, df_locais, chaves_merge)

    salvar_csv(df_dados_finais, path_saida)
    print(df_dados_finais.head())


if __name__ == "__main__":
    main()
