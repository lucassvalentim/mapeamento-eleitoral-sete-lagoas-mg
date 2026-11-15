import os
import zipfile
from pathlib import Path
import requests

# Diretório base de destino
BASE_DIR = Path("./dados/brutos")

URLS = [
    "https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_secao/votacao_secao_2026_BR.zip",
    "https://cdn.tse.jus.br/estatistica/sead/odsele/eleitorado_locais_votacao/eleitorado_local_votacao_2026.zip",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def baixar_arquivo(url: str, destino: Path) -> Path:
    nome_arquivo = url.split("/")[-1]
    caminho_zip = destino / nome_arquivo
    print(f"Baixando {nome_arquivo}...")

    with requests.get(url, headers=HEADERS, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(caminho_zip, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

    print(f"Download concluído: {caminho_zip}")
    return caminho_zip


def extrair_e_limpar(caminho_zip: Path, destino_base: Path, manter_apenas: set[str] | None = None):
    # Cria uma subpasta com o nome do arquivo .zip (ex: votacao_secao_2026_BR)
    pasta_extracao = destino_base / caminho_zip.stem
    pasta_extracao.mkdir(parents=True, exist_ok=True)

    print(f"Extraindo {caminho_zip.name} para {pasta_extracao}/...")
    with zipfile.ZipFile(caminho_zip, "r") as zf:
        if manter_apenas is None:
            zf.extractall(pasta_extracao)
            for membro in zf.namelist():
                print(f"  -> Extraído: {membro}")
        else:
            permitidos_lower = {nome.lower() for nome in manter_apenas}
            for membro in zf.namelist():
                nome_base = os.path.basename(membro).lower()
                if nome_base in permitidos_lower:
                    zf.extract(membro, pasta_extracao)
                    print(f"  -> Mantido: {membro}")

    # Remove o .zip original
    caminho_zip.unlink()
    print(f"Arquivo compactado removido: {caminho_zip.name}\n")


def main():
    BASE_DIR.mkdir(parents=True, exist_ok=True)

    # Votação por seção (extrai tudo, preservando os dados e o seu leiame.pdf próprio)
    zip_votacao = baixar_arquivo(URLS[0], BASE_DIR)
    extrair_e_limpar(zip_votacao, BASE_DIR, manter_apenas=None)

    # Locais de votação (mantém apenas MG e o seu leiame.pdf próprio)
    zip_eleitorado = baixar_arquivo(URLS[1], BASE_DIR)
    arquivos_desejados = {
        "eleitorado_local_votacao_2026_MG.csv",
        "eleitorado_local_votacao_2026_MG.cvs",
        "leiame.pdf",
        "leaime.pdf",
    }
    extrair_e_limpar(zip_eleitorado, BASE_DIR, manter_apenas=arquivos_desejados)

    print("Processo finalizado com sucesso!")


if __name__ == "__main__":
    main()