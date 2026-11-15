#!/usr/bin/env bash
set -e

PROJETO_DIR="$(pwd)"
ENV_NAME="eleicoes_sl"

echo "=== 1. Organizando estrutura de diretórios ==="
mkdir -p "$PROJETO_DIR/dados/brutos"
mkdir -p "$PROJETO_DIR/dados/processados"
mkdir -p "$PROJETO_DIR/scripts"
mkdir -p "$PROJETO_DIR/mapas"

cd "$PROJETO_DIR"

echo "=== 2. Configurando e ativando ambiente Conda ($ENV_NAME) ==="
eval "$(conda shell.bash hook)"

if ! conda info --envs | grep -q "^$ENV_NAME "; then
    echo "Ambiente '$ENV_NAME' não encontrado. Criando a partir de environment.yml..."
    conda env create -f "$PROJETO_DIR/environment.yml"
else
    echo "Ambiente '$ENV_NAME' já existe."
fi

conda activate "$ENV_NAME"

# Impede que pacotes instalados em ~/.local interfiram no ambiente Conda
export PYTHONNOUSERSITE=1

echo "=== 3. Executando download dos dados do TSE ==="
python "$PROJETO_DIR/scripts/baixar_dados_tse.py"

echo "=== 4. Executando coleta e processamento dos dados ==="
python "$PROJETO_DIR/scripts/coleta_processa_dados.py"

echo "=== Pipeline finalizado com sucesso! ==="