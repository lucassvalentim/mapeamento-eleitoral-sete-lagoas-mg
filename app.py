import streamlit as st
import pandas as pd
import geopandas as gpd
import numpy as np
import folium
from streamlit_folium import st_folium
import branca.colormap as cm
from shapely.geometry import Point, box
from shapely.ops import voronoi_diagram
import plotly.express as px
import requests

# ==============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA E ESTILIZAÇÃO
# Decisão de Design: Layout wide com fontes ampliadas para facilitar a leitura
# dos KPIs, rótulos dos gráficos e tooltips geoespaciais.
# ==============================================================================
st.set_page_config(
    page_title="Mapeamento Eleitoral - Sete Lagoas (UFSJ)",
    page_icon="🗳️",
    layout="wide"
)

st.markdown("""
    <style>
    html, body, [class*="css"] {
        font-size: 17px;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 18px;
        font-weight: 600;
    }
    [data-testid="stMetricValue"] {
        font-size: 32px;
    }
    [data-testid="stMetricLabel"] {
        font-size: 17px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("Análise Espacial e Eleitoral — Sete Lagoas (MG)")

# ==============================================================================
# 2. MAPEAMENTO DE CORES PARTIDÁRIAS FIXAS (ELEIÇÕES 2026)
# Decisão de Design: Consistência visual entre gráficos e mapas utilizando
# Vermelho para Lula (PT), Verde para Flávio Bolsonaro (PL) e cores distintas
# baseadas nas paletas partidárias dos demais candidatos.
# ==============================================================================
def obter_cor_partido(nome_candidato):
    nome = nome_candidato.upper()
    if "LULA" in nome:
        return "#dc2626"  # PT - Vermelho
    elif "BOLSONARO" in nome:
        return "#16a34a"  # PL - Verde
    elif "AUGUSTO" in nome or "CURY" in nome:
        return "#2563eb"  # MDB / PSDB - Azul Royal
    elif "CAIADO" in nome or "RONALDO" in nome:
        return "#0284c7"  # União Brasil - Azul Celeste
    elif "RENAN" in nome:
        return "#eab308"  # Missão - Amarelo
    elif "ZEMA" in nome or "ROMEU" in nome:
        return "#f97316"  # Novo - Laranja
    elif "SAMARA" in nome:
        return "#1e293b"  # UP - Preto / Ardósia
    elif "CLARIANA" in nome:
        return "#881337"  # PCO / PSTU - Bordô
    elif "HERTZ" in nome:
        return "#9f1239"  # PSTU - Carmesim
    elif "EDMILSON" in nome:
        return "#7f1d1d"  # PCB - Vermelho Escuro
    elif "RUI" in nome or "PIMENTA" in nome:
        return "#b91c1c"  # PCO - Terracota
    elif "WILSON" in nome or "GRASSI" in nome:
        return "#1e3a8a"  # DC - Azul Marinho
    elif "LEONARDO" in nome or "LEO" in nome or "LÉO" in nome or "PERICLES" in nome or "PÉRICLES" in nome:
        return "#334155"  # UP - Cinza Chumbo
    elif "BRANCO" in nome:
        return "#94a3b8"
    elif "NULO" in nome:
        return "#475569"
    else:
        return "#6d28d9"

def obter_paleta_folium(candidato):
    """Retorna escala sequencial para o preenchimento dos polígonos vencidos."""
    nome = candidato.upper()
    cor_principal = obter_cor_partido(candidato)
    if "LULA" in nome:
        return cm.LinearColormap(['#fecaca', '#ef4444', '#991b1b']), '#991b1b'
    elif "BOLSONARO" in nome:
        return cm.LinearColormap(['#bbf7d0', '#22c55e', '#14532d']), '#14532d'
    else:
        return cm.LinearColormap(['#e2e8f0', cor_principal]), cor_principal

# ==============================================================================
# 3. CARREGAMENTO DOS DADOS E TESSELAÇÃO DE VORONOI
# Decisão Metodológica: Como o TSE disponibiliza pontos geográficos exatos
# dos locais de votação, aplica-se o diagrama de Voronoi recortado pela malha
# municipal oficial do IBGE (código 3167202 - Sete Lagoas) para representar
# áreas de influência espacial contínua sem sobreposição.
# ==============================================================================
@st.cache_data(show_spinner="Carregando dados e gerando malha espacial...")
def carregar_dados_e_malha():
    df = pd.read_csv('dados/processados/votacao_geolocalizada.csv', sep=';')
    df = df.dropna(subset=['NR_LATITUDE', 'NR_LONGITUDE']).copy()
    
    df['IS_VALIDO'] = ~df['NM_VOTAVEL'].str.upper().isin(['VOTO BRANCO', 'VOTO NULO'])
    
    poligono_cidade = None
    try:
        url_sl = "https://servicodados.ibge.gov.br/api/v3/malhas/municipios/3167202?formato=application/vnd.geo+json"
        resp = requests.get(url_sl, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        if resp.status_code == 200:
            gdf_mun = gpd.read_file(resp.text).to_crs(epsg=4326)
            poligono_cidade = gdf_mun.geometry.union_all()
    except Exception:
        pass

    locais = (
        df[['NR_ZONA', 'NM_BAIRRO', 'NM_LOCAL_VOTACAO', 'NR_LATITUDE', 'NR_LONGITUDE']]
        .drop_duplicates(subset=['NR_LATITUDE', 'NR_LONGITUDE'])
        .reset_index(drop=True)
    )
    locais['id_local'] = locais.index.astype(str)
    df = df.merge(locais[['NR_LATITUDE', 'NR_LONGITUDE', 'id_local']], on=['NR_LATITUDE', 'NR_LONGITUDE'], how='left')

    pontos = gpd.GeoSeries([Point(xy) for xy in zip(locais['NR_LONGITUDE'], locais['NR_LATITUDE'])], crs="EPSG:4326")
    minx, miny, maxx, maxy = pontos.total_bounds
    envelope = poligono_cidade.buffer(0.05) if poligono_cidade is not None else box(minx - 0.02, miny - 0.02, maxx + 0.02, maxy + 0.02)
    recorte_final = poligono_cidade if poligono_cidade is not None else envelope

    regioes_voronoi = voronoi_diagram(pontos.union_all(), envelope=envelope)
    poligonos = []
    for _, row in locais.iterrows():
        ponto = Point(row['NR_LONGITUDE'], row['NR_LATITUDE'])
        poly = next((g.intersection(recorte_final) for g in regioes_voronoi.geoms if g.contains(ponto) or g.touches(ponto)), None)
        poligonos.append(poly)

    gdf_locais = gpd.GeoDataFrame(locais, geometry=poligonos, crs="EPSG:4326")
    gdf_locais = gdf_locais[gdf_locais.geometry.notnull()].copy()
    bounds_sl = [[miny - 0.015, minx - 0.015], [maxy + 0.015, maxx + 0.015]]

    candidatos_unicos = sorted(df['NM_VOTAVEL'].unique().tolist())
    cores_candidatos = {cand: obter_cor_partido(cand) for cand in candidatos_unicos}

    return df, gdf_locais, bounds_sl, cores_candidatos

df, gdf_locais, bounds_sl, CORES_CANDIDATOS = carregar_dados_e_malha()

# ==============================================================================
# 4. BARRA LATERAL (FILTROS INTERATIVOS)
# ==============================================================================

turno_selecionado = st.sidebar.radio(
    "Turno:",
    options=[1, 2],
    format_func=lambda x: f"{x}º Turno",
    index=1
)

zonas_disponiveis = sorted(df['NR_ZONA'].unique().tolist())
zonas_selecionadas = st.sidebar.multiselect(
    "Zona Eleitoral:",
    options=zonas_disponiveis,
    default=zonas_disponiveis
)

incluir_brancos_nulos = st.sidebar.checkbox("Incluir Brancos e Nulos nos gráficos", value=False)

df_turno = df[(df['NR_TURNO'] == turno_selecionado) & (df['NR_ZONA'].isin(zonas_selecionadas))].copy()
df_validos = df_turno[df_turno['IS_VALIDO']].copy()
df_analise = df_turno if incluir_brancos_nulos else df_validos

# ==============================================================================
# 5. INDICADORES PRINCIPAIS (KPIs)
# ==============================================================================
total_votos_validos = int(df_validos['QT_VOTOS'].sum())
total_brancos_nulos = int(df_turno[~df_turno['IS_VALIDO']]['QT_VOTOS'].sum())
ranking_geral = df_validos.groupby('NM_VOTAVEL')['QT_VOTOS'].sum().sort_values(ascending=False)

lider_nome = ranking_geral.index[0] if len(ranking_geral) > 0 else "N/A"
lider_votos = int(ranking_geral.iloc[0]) if len(ranking_geral) > 0 else 0
lider_perc = (lider_votos / total_votos_validos * 100) if total_votos_validos > 0 else 0

segundo_nome = ranking_geral.index[1] if len(ranking_geral) > 1 else "N/A"
segundo_votos = int(ranking_geral.iloc[1]) if len(ranking_geral) > 1 else 0
segundo_perc = (segundo_votos / total_votos_validos * 100) if total_votos_validos > 0 else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Votos Válidos", f"{total_votos_validos:,}".replace(",", "."))
col2.metric(f"1º Lugar ({lider_nome.split()[0]})", f"{lider_perc:.2f}%", f"{lider_votos:,} votos".replace(",", "."))
col3.metric(f"2º Lugar ({segundo_nome.split()[0]})", f"{segundo_perc:.2f}%", f"{segundo_votos:,} votos".replace(",", "."))
col4.metric("Brancos e Nulos", f"{total_brancos_nulos:,}".replace(",", "."), f"{len(df_turno['id_local'].unique())} locais")

st.divider()

# ==============================================================================
# 6. FUNÇÕES DE CONSTRUÇÃO DOS MAPAS FOLIUM
# ==============================================================================
def preparar_dados_espaciais(df_base):
    totais = df_base.groupby('id_local')['QT_VOTOS'].sum().reset_index(name='total_votos')
    votos = df_base.groupby(['id_local', 'NM_VOTAVEL'])['QT_VOTOS'].sum().reset_index().merge(totais, on='id_local')
    votos['percentual'] = (votos['QT_VOTOS'] / votos['total_votos'] * 100).round(2)

    vencedores = votos.sort_values('QT_VOTOS', ascending=False).drop_duplicates('id_local')[['id_local', 'NM_VOTAVEL', 'percentual']]
    vencedores = vencedores.rename(columns={'NM_VOTAVEL': 'vencedor', 'percentual': 'perc_vencedor'})

    top3_por_local = (
        votos.sort_values(['id_local', 'QT_VOTOS'], ascending=[True, False])
        .groupby('id_local')
        .head(3)
    )
    resumo_placar = (
        top3_por_local.assign(txt=lambda d: d['NM_VOTAVEL'].str.split().str[0] + ': ' + d['percentual'].astype(str) + '%')
        .groupby('id_local')['txt']
        .apply(lambda s: ' | '.join(s))
        .reset_index(name='placar_texto')
    )

    pivot_perc = votos.pivot(index='id_local', columns='NM_VOTAVEL', values='percentual').fillna(0).reset_index()
    pivot_perc = pivot_perc.merge(vencedores, on='id_local', how='left').merge(resumo_placar, on='id_local', how='left')

    gdf_mapa = gdf_locais.merge(pivot_perc, on='id_local', how='inner')
    gdf_mapa['lider_texto'] = gdf_mapa['vencedor'] + ' (' + gdf_mapa['perc_vencedor'].astype(str) + '%)'
    return gdf_mapa, votos

def construir_mapa_dominancia_geral(df_base, turno):
    """Pinta cada área com a cor partidária do candidato que venceu naquele local."""
    gdf_mapa, _ = preparar_dados_espaciais(df_base)

    mapa = folium.Map(
        location=[-19.4658, -44.2467],
        zoom_start=12,
        min_zoom=11,
        tiles='OpenStreetMap'
    )
    mapa.fit_bounds(bounds_sl)

    escalas_candidatos = {}
    for cand in df_base['NM_VOTAVEL'].unique():
        paleta, _ = obter_paleta_folium(cand)
        vitorias = gdf_mapa[gdf_mapa['vencedor'] == cand]['perc_vencedor']
        vmin = vitorias.min() if len(vitorias) > 0 else 30
        vmax = vitorias.max() if len(vitorias) > 0 else 70
        if vmin == vmax:
            vmin = max(0, vmin - 10)
        escalas_candidatos[cand] = paleta.scale(vmin, vmax)

    def style_fn(feature):
        props = feature['properties']
        vencedor = props.get('vencedor')
        perc = props.get('perc_vencedor', 50)
        if vencedor in escalas_candidatos:
            cor_fill = escalas_candidatos[vencedor](perc)
            return {'fillColor': cor_fill, 'color': '#2c3e50', 'weight': 1.5, 'fillOpacity': 0.74}
        return {'fillColor': 'transparent', 'color': '#636e72', 'weight': 1, 'fillOpacity': 0.0}

    tooltip = folium.GeoJsonTooltip(
        fields=['NR_ZONA', 'NM_BAIRRO', 'NM_LOCAL_VOTACAO', 'lider_texto', 'placar_texto'],
        aliases=['Zona:', 'Bairro:', 'Local de Votação:', f'Líder ({turno}º T):', 'Top Candidatos:'],
        localize=True,
        labels=True,
        style="background-color: #fff; border: 2px solid #2c3e50; border-left: 6px solid #2c3e50; border-radius: 6px; font-family: Arial; font-size: 13px; padding: 8px;"
    )

    folium.GeoJson(
        gdf_mapa,
        name=f"Dominância Geral ({turno}º Turno)",
        style_function=style_fn,
        tooltip=tooltip
    ).add_to(mapa)

    cands_turno = df_base.groupby('NM_VOTAVEL')['QT_VOTOS'].sum().sort_values(ascending=False).index.tolist()
    itens_legenda = ""
    for cand in cands_turno:
        cor = CORES_CANDIDATOS[cand]
        qtd_vitorias = int((gdf_mapa['vencedor'] == cand).sum())
        itens_legenda += f"""
        <div style="display: flex; align-items: center; margin-bottom: 5px;">
            <span style="background:{cor}; width:15px; height:15px; display:inline-block; margin-right:8px; border:1px solid #333; border-radius:3px;"></span>
            <span><b>{cand}</b> ({qtd_vitorias} locais)</span>
        </div>
        """

    legenda_html = f"""
    <div style="position: fixed; bottom: 25px; left: 25px; z-index: 9999; background-color: rgba(255, 255, 255, 0.95);
                padding: 12px 15px; border: 2px solid #2c3e50; border-radius: 8px; font-family: Arial; font-size: 13px;
                box-shadow: 0 2px 6px rgba(0,0,0,0.25); max-height: 280px; overflow-y: auto;">
        <div style="font-weight: bold; margin-bottom: 8px; font-size: 14px; border-bottom: 1px solid #ccc; padding-bottom: 4px;">
            Candidatos — {turno}º Turno
        </div>
        {itens_legenda}
    </div>
    """
    mapa.get_root().html.add_child(folium.Element(legenda_html))
    folium.LayerControl().add_to(mapa)

    return mapa

def construir_mapa_individual_dominancia(df_base, turno, candidato):
    """
    Regra estrita: pinta SOMENTE as áreas onde o candidato selecionado venceu.
    Se ele não venceu nenhuma área, nenhuma área é pintada (preenchimento transparente).
    O tooltip exibe exclusivamente os dados do candidato selecionado.
    """
    gdf_mapa, votos_detalhe = preparar_dados_espaciais(df_base)
    
    # Filtra votos absolutos e percentuais exclusivamente do candidato escolhido
    votos_cand = votos_detalhe[votos_detalhe['NM_VOTAVEL'] == candidato][['id_local', 'QT_VOTOS', 'percentual']].copy()
    votos_cand = votos_cand.rename(columns={'QT_VOTOS': 'votos_cand', 'percentual': 'perc_cand'})
    
    gdf_ind = gdf_mapa[['id_local', 'NR_ZONA', 'NM_BAIRRO', 'NM_LOCAL_VOTACAO', 'vencedor', 'geometry']].merge(
        votos_cand, on='id_local', how='left'
    )
    gdf_ind['votos_cand'] = gdf_ind['votos_cand'].fillna(0).astype(int)
    gdf_ind['perc_cand'] = gdf_ind['perc_cand'].fillna(0.0)
    gdf_ind['resultado_cand'] = gdf_ind['votos_cand'].astype(str) + ' votos (' + gdf_ind['perc_cand'].astype(str) + '%)'

    mapa = folium.Map(
        location=[-19.4658, -44.2467],
        zoom_start=12,
        min_zoom=11,
        tiles='OpenStreetMap'
    )
    mapa.fit_bounds(bounds_sl)

    paleta_base, cor_destaque = obter_paleta_folium(candidato)
    vitorias_cand = gdf_ind[gdf_ind['vencedor'] == candidato]['perc_cand']
    tem_vitorias = len(vitorias_cand) > 0

    if tem_vitorias:
        vmin = vitorias_cand.min()
        vmax = vitorias_cand.max()
        if vmin == vmax:
            vmin = max(0, vmin - 5)
            vmax = vmax + 5
        colormap = paleta_base.scale(vmin, vmax)
        colormap.caption = f'{turno}º Turno: Áreas Vencidas por {candidato} (%)'
        colormap.add_to(mapa)
    else:
        colormap = None

    def style_fn(feature):
        props = feature['properties']
        # Pinta SOMENTE se o candidato venceu no local; caso contrário, não pinta nada
        if tem_vitorias and props.get('vencedor') == candidato:
            val = props.get('perc_cand', 0)
            return {'fillColor': colormap(val), 'color': '#2c3e50', 'weight': 1.5, 'fillOpacity': 0.74}
        return {'fillColor': 'transparent', 'color': '#64748b', 'weight': 1.0, 'fillOpacity': 0.0}

    # Tooltip exibindo SOMENTE a informação do candidato selecionado
    tooltip = folium.GeoJsonTooltip(
        fields=['NR_ZONA', 'NM_BAIRRO', 'NM_LOCAL_VOTACAO', 'resultado_cand'],
        aliases=['Zona:', 'Bairro:', 'Local de Votação:', f'{candidato} ({turno}º T):'],
        localize=True,
        labels=True,
        style=f"background-color: #fff; border: 2px solid {cor_destaque}; border-left: 6px solid {cor_destaque}; border-radius: 6px; font-family: Arial; font-size: 13px; padding: 8px;"
    )

    folium.GeoJson(
        gdf_ind,
        name=candidato,
        style_function=style_fn,
        tooltip=tooltip
    ).add_to(mapa)
    folium.LayerControl().add_to(mapa)

    return mapa

# ==============================================================================
# 7. ABAS DO DASHBOARD
# ==============================================================================
tab_mapas, tab_candidatos, tab_bairros, tab_dados = st.tabs([
    "🗺️ Mapas Geoespaciais",
    "📊 Todos os Candidatos",
    "🏘️ Análise por Bairro e Zona",
    "📋 Tabela de Dados"
])

# --- ABA 1: MAPAS ---
with tab_mapas:
    sub_mapa1, sub_mapa2 = st.tabs([
        "🏆 Mapa por Dominância (Todos os Candidatos)",
        "🔍 Mapa Individual por Candidato"
    ])

    with sub_mapa1:
        st.subheader(f"Dominância Territorial — {turno_selecionado}º Turno")
        if len(df_validos) > 0:
            mapa_dom = construir_mapa_dominancia_geral(df_validos, turno_selecionado)
            st_folium(mapa_dom, width=None, height=620, returned_objects=[])
        else:
            st.warning("Selecione pelo menos uma zona eleitoral na barra lateral.")

    with sub_mapa2:
        st.subheader(f"Mapa Individual — {turno_selecionado}º Turno")
        lista_cands = ranking_geral.index.tolist()
        cand_escolhido = st.selectbox("Selecione o Candidato:", options=lista_cands)

        if cand_escolhido and len(df_validos) > 0:
            mapa_ind = construir_mapa_individual_dominancia(df_validos, turno_selecionado, cand_escolhido)
            st_folium(mapa_ind, width=None, height=620, returned_objects=[])

# --- ABA 2: TODOS OS CANDIDATOS ---
with tab_candidatos:
    st.subheader(f"Desempenho por Candidato — {turno_selecionado}º Turno")
    
    resumo_cands = (
        df_analise.groupby(['NR_VOTAVEL', 'NM_VOTAVEL'], as_index=False)['QT_VOTOS']
        .sum()
        .sort_values('QT_VOTOS', ascending=False)
    )
    resumo_cands['Percentual (%)'] = (resumo_cands['QT_VOTOS'] / resumo_cands['QT_VOTOS'].sum() * 100).round(2)

    sub_c1, sub_c2 = st.tabs([
        "📊 Ranking Total e Proporção",
        "📈 Comparativo 1º vs 2º Turno"
    ])

    with sub_c1:
        col_g1, col_g2 = st.columns([3, 2])
        with col_g1:
            fig_bar = px.bar(
                resumo_cands,
                x='QT_VOTOS',
                y='NM_VOTAVEL',
                orientation='h',
                text='Percentual (%)',
                color='NM_VOTAVEL',
                color_discrete_map=CORES_CANDIDATOS,
                title=f"Total de Votos por Candidato ({turno_selecionado}º Turno)",
                labels={'QT_VOTOS': 'Quantidade de Votos', 'NM_VOTAVEL': 'Candidato'}
            )
            fig_bar.update_traces(
                texttemplate='<b>%{text:.2f}%</b>',
                textposition='outside',
                textfont=dict(size=15)
            )
            fig_bar.update_layout(
                yaxis={'categoryorder': 'total ascending', 'tickfont': {'size': 15}, 'title': {'font': {'size': 16}}},
                xaxis={'tickfont': {'size': 14}, 'title': {'font': {'size': 16}}, 'range': [0, resumo_cands['QT_VOTOS'].max() * 1.18]},
                title={'font': {'size': 20}},
                font=dict(size=15),
                showlegend=False,
                height=520
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        with col_g2:
            fig_pie = px.pie(
                resumo_cands,
                values='QT_VOTOS',
                names='NM_VOTAVEL',
                color='NM_VOTAVEL',
                color_discrete_map=CORES_CANDIDATOS,
                hole=0.42,
                title="Fatia de Votos no Município"
            )
            fig_pie.update_traces(
                textposition='inside',
                textinfo='percent+label',
                textfont=dict(size=15)
            )
            fig_pie.update_layout(
                title={'font': {'size': 20}},
                font=dict(size=15),
                showlegend=False,
                height=520
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    with sub_c2:
        df_comp = df[(df['NR_ZONA'].isin(zonas_selecionadas)) & (df['IS_VALIDO'])].copy()
        comp_turnos = df_comp.groupby(['NR_TURNO', 'NM_VOTAVEL'], as_index=False)['QT_VOTOS'].sum()
        comp_turnos['Turno'] = comp_turnos['NR_TURNO'].astype(str) + "º Turno"

        fig_comp = px.bar(
            comp_turnos,
            x='NM_VOTAVEL',
            y='QT_VOTOS',
            color='NM_VOTAVEL',
            color_discrete_map=CORES_CANDIDATOS,
            facet_col='Turno',
            text_auto=True,
            title="Comparação Direta de Votos: 1º Turno vs. 2º Turno",
            labels={'NM_VOTAVEL': 'Candidato', 'QT_VOTOS': 'Votos'}
        )
        fig_comp.update_traces(textfont=dict(size=15), textposition='outside')
        fig_comp.update_xaxes(categoryorder='total descending', tickfont=dict(size=14), title_font=dict(size=16))
        fig_comp.update_yaxes(tickfont=dict(size=14), title_font=dict(size=16), range=[0, comp_turnos['QT_VOTOS'].max() * 1.15])
        fig_comp.update_layout(
            title={'font': {'size': 20}},
            font=dict(size=15),
            showlegend=False,
            height=540
        )
        fig_comp.for_each_annotation(lambda a: a.update(text=f"<b>{a.text.split('=')[-1]}</b>", font=dict(size=17)))
        st.plotly_chart(fig_comp, use_container_width=True)

# --- ABA 3: BAIRROS E ZONAS ---
with tab_bairros:
    st.subheader(f"Análise Territorial por Bairro e Zona Eleitoral ({turno_selecionado}º Turno)")
    
    sub_b1, sub_b2 = st.tabs(["🏘️ Top Bairros por Candidato", "🧭 Comparativo entre Zonas Eleitorais"])
    
    with sub_b1:
        top_n = st.slider("Número de bairros para exibir:", min_value=5, max_value=30, value=15)
        bairros_tot = df_validos.groupby('NM_BAIRRO')['QT_VOTOS'].sum().nlargest(top_n).index
        df_top_bairros = df_validos[df_validos['NM_BAIRRO'].isin(bairros_tot)].groupby(['NM_BAIRRO', 'NM_VOTAVEL'], as_index=False)['QT_VOTOS'].sum()

        fig_bairros = px.bar(
            df_top_bairros,
            x='QT_VOTOS',
            y='NM_BAIRRO',
            color='NM_VOTAVEL',
            color_discrete_map=CORES_CANDIDATOS,
            orientation='h',
            title=f"Distribuição de Votos nos {top_n} Maiores Bairros",
            labels={'QT_VOTOS': 'Total de Votos', 'NM_BAIRRO': 'Bairro', 'NM_VOTAVEL': 'Candidato'}
        )
        fig_bairros.update_layout(
            yaxis={'categoryorder': 'total ascending', 'tickfont': {'size': 14}},
            xaxis={'tickfont': {'size': 14}},
            title={'font': {'size': 20}},
            font=dict(size=15),
            height=580
        )
        st.plotly_chart(fig_bairros, use_container_width=True)

    with sub_b2:
        df_zonas = df_validos.groupby(['NR_ZONA', 'NM_VOTAVEL'], as_index=False)['QT_VOTOS'].sum()
        df_zonas['NR_ZONA'] = "Zona " + df_zonas['NR_ZONA'].astype(str)
        fig_zonas = px.bar(
            df_zonas,
            x='NR_ZONA',
            y='QT_VOTOS',
            color='NM_VOTAVEL',
            color_discrete_map=CORES_CANDIDATOS,
            barmode='group',
            text_auto=True,
            title="Votação por Zona Eleitoral (263, 264 e 322)",
            labels={'NR_ZONA': 'Zona Eleitoral', 'QT_VOTOS': 'Votos', 'NM_VOTAVEL': 'Candidato'}
        )
        fig_zonas.update_traces(textfont=dict(size=14), textposition='outside')
        fig_zonas.update_layout(
            title={'font': {'size': 20}},
            font=dict(size=15),
            height=520
        )
        st.plotly_chart(fig_zonas, use_container_width=True)

# --- ABA 4: TABELA DE DADOS ---
with tab_dados:
    st.subheader("Tabela Detalhada por Local de Votação")
    tabela_exibicao = (
        df_analise.groupby(['NR_TURNO', 'NR_ZONA', 'NM_BAIRRO', 'NM_LOCAL_VOTACAO', 'NR_VOTAVEL', 'NM_VOTAVEL'], as_index=False)['QT_VOTOS']
        .sum()
        .sort_values(['NR_ZONA', 'NM_BAIRRO', 'QT_VOTOS'], ascending=[True, True, False])
    )
    st.dataframe(tabela_exibicao, use_container_width=True)

    csv_download = tabela_exibicao.to_csv(index=False, sep=';').encode('utf-8')
    st.download_button(
        label="📥 Baixar Tabela Filtrada (CSV)",
        data=csv_download,
        file_name=f"votacao_sete_lagoas_{turno_selecionado}turno.csv",
        mime="text/csv"
    )