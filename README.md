# Eleições 2026 — Sete Lagoas (MG)

Pipeline automatizado para captura, filtragem e georreferenciamento dos dados eleitorais de Sete Lagoas (MG) a partir dos repositórios oficiais do Tribunal Superior Eleitoral (TSE).

O processamento consolida uma base de dados final que cruza as **zonas e locais de votação** com suas **coordenadas geográficas** e a **pontuação (totalização de votos) obtida no 1º e no 2º turno**.

## Estrutura do Projeto

```
mapeamento-eleitoral-sete-lagoas-mg/
├── dados/
│   ├── brutos/          # Arquivos originais baixados e extraídos do TSE
│   └── processados/     # Base final consolidada (zonas + geolocalização + 1º e 2º turnos)
├── mapas/               # Mapas interativos gerados com Folium
├── scripts/
│   ├── baixar_dados_tse.py        # Captura os dados na internet e extrai os arquivos
│   └── coleta_processa_dados.py   # Filtra Sete Lagoas, cruza coordenadas e consolida turnos
├── environment.yml      # Especificação do ambiente Conda (pandas, geopandas, folium)
├── rodar_pipeline.sh    # Script principal de automação
└── README.md
```

## Pré-requisitos

- Sistema operacional Linux
- **Miniconda** ou **Anaconda** instalado e configurado no terminal

## Como Executar

Para preparar o ambiente, baixar os dados da internet e gerar a base final processada, basta dar permissão de execução ao script `rodar_pipeline.sh` e executá-lo:

```
# Acesse a pasta do projeto
cd mapeamento-eleitoral-sete-lagoas-mg

# Ative a permissão de execução do script (necessário apenas na primeira vez)
chmod +x rodar_pipeline.sh

# Execute o pipeline completo
./rodar_pipeline.sh
```

## O que o Pipeline Faz

Ao rodar o `./rodar_pipeline.sh`, as seguintes etapas são executadas automaticamente:

1. **Organização de Pastas:** Cria os diretórios necessários (`dados/brutos`, `dados/processados`, `scripts` e `mapas`).
2. **Configuração do Ambiente:** Cria (caso ainda não exista) e ativa o ambiente Conda `eleicoes_sl` com todas as dependências geoespaciais isoladas.
3. **Captura dos Dados (`baixar_dados_tse.py`):** Baixa os pacotes de votação por seção (`votacao_secao_2026_BR.zip`) e de locais de votação (`eleitorado_local_votacao_2026.zip`) diretamente do portal de Dados Abertos do TSE, mantendo apenas os arquivos necessários (pula o download automaticamente se os arquivos já estiverem em disco).
4. **Processamento e Consolidação (`coleta_processa_dados.py`):** Filtra os registros de Sete Lagoas (MG), associa cada zona/local às suas respectivas posições geográficas (latitude e longitude) e estrutura a pontuação final do **1º e 2º turno** em `dados/processados/`.
