# Mapeamento Eleitoral — Sete Lagoas (MG) | Eleições 2026

Dashboard interativo e pipeline automatizado para captura, filtragem e georreferenciamento dos dados eleitorais de **Sete Lagoas (MG)** a partir dos repositórios oficiais do Tribunal Superior Eleitoral (TSE) e da malha municipal do IBGE.

O projeto consolida uma base geoespacial cruzando as **zonas e locais de votação** com suas **coordenadas geográficas** e a **votação obtida por candidato no 1º e no 2º turno**, disponibilizando a análise em um aplicativo web interativo construído com **Streamlit**, **Folium** e **Plotly**.

## Acesso ao Dashboard

A aplicação está publicada e acessível online via **Streamlit Community Cloud**:

- **Link:** <a>`https://mapeamento-eleitoral-sete-lagoas-mg.streamlit.app/`</a>

### Executar Localmente

Caso deseje rodar o dashboard na sua própria máquina (utilizando a base processada já disponível no repositório):

```bash
# Instale as dependências da aplicação web
pip install -r requirements.txt

# Inicie o servidor local do Streamlit
streamlit run app.py
```

## Estrutura do Repositório

```text
mapeamento-eleitoral-sete-lagoas-mg/
├── app.py                         # Aplicação principal do dashboard interativo (Streamlit)
├── requirements.txt               # Dependências Python utilizadas no deploy (Streamlit Cloud)
├── rodar_pipeline.sh              # Script Bash para criar o ambiente virtual e automatizar o pipeline
├── enviroment/
│   └── enviroment.yml             # Especificação completa do ambiente Conda para ETL e geoprocessamento
├── dados/
│   ├── brutos/                    # [Não versionado] Arquivos originais baixados e extraídos do TSE
│   └── processados/
│       └── votacao_geolocalizada.csv  # Base final já consolidada (zonas + coordenadas + 1º e 2º turnos)
├── scripts/
│   ├── baixar_dados_tse.py        # Baixa e extrai os arquivos oficiais do portal de Dados Abertos do TSE
│   └── coleta_processa_dados.py   # Filtra Sete Lagoas (MG), cruza coordenadas e gera a base final
└── README.md
```

## Simulação de Coleta e Processamento dos Dados
### Pré-requisitos (Para Execução do Pipeline de Dados)

- Sistema operacional **Linux** (ou WSL no Windows)
- **Miniconda** ou **Anaconda** instalado e configurado no terminal

### Ambiente Virtual e Obtenção dos Dados Brutos

Por conta do tamanho elevado dos arquivos originais divulgados pelo TSE, a pasta `dados/brutos/` **não está incluída neste repositório**.

Para criar o ambiente virtual e baixar os dados brutos automaticamente, execute o script Bash na raiz do projeto:

```bash
# 1. Acesse a pasta do projeto
cd mapeamento-eleitoral-sete-lagoas-mg

# 2. Conceda permissão de execução ao script Bash (necessário apenas na primeira vez)
chmod +x rodar_pipeline.sh

# 3. Execute o script para criar o ambiente virtual e rodar o pipeline
./rodar_pipeline.sh
```

#### O que o `./rodar_pipeline.sh` executa:

1. **Estruturação de Diretórios:** Garante a existência das pastas `dados/brutos` e `dados/processados`.
2. **Criação do Ambiente Virtual (`eleicoes_sl`):** Cria (caso ainda não exista) e ativa o ambiente Conda a partir de `enviroment/enviroment.yml` com todas as bibliotecas geoespaciais configuradas.
3. **Download dos Dados Brutos (`scripts/baixar_dados_tse.py`):** Captura e extrai automaticamente os arquivos `votacao_secao_2026_BR.zip` e `eleitorado_local_votacao_2026.zip` diretamente do portal de Dados Abertos do TSE para `dados/brutos/` (caso os arquivos já existam localmente, o download é pulado).
4. **Processamento (`scripts/coleta_processa_dados.py`):** Consolida os dados em `dados/processados/votacao_geolocalizada.csv`.

### Base de Dados Processada e Recriação

- **Base pronta para uso:** O arquivo principal `dados/processados/votacao_geolocalizada.csv` **já está criado e versionado** neste repositório, permitindo executar o dashboard (`app.py`) ou realizar análises imediatamente sem precisar baixar os arquivos brutos.
- **Como gerar a base novamente:** Caso queira reprocessar os dados do zero ou atualizar a base a partir de novos arquivos do TSE, certifique-se de que os arquivos originais estejam em `dados/brutos/` (via `python scripts/baixar_dados_tse.py`) e execute o script de processamento com o ambiente virtual ativado:

```bash
conda activate eleicoes_sl
python scripts/coleta_processa_dados.py
```

Esse comando filtrará novamente os registros do município de Sete Lagoas (código TSE `53430`), associará as coordenadas geográficas de cada local de votação e sobrescreverá `dados/processados/votacao_geolocalizada.csv` com a consolidação do **1º e do 2º turno**.
