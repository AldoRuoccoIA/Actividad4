# app.py
# Dash app para Análisis de Mortalidad No Fetal 2019
# Archivos esperados en data/: NoFetal2019.xlsx, Divipola.xlsx, CodigosDeMuerte.xlsx
# Requisitos: pandas, numpy, plotly, dash, dash-bootstrap-components, openpyxl, gunicorn

import os
import json
from pathlib import Path

import pandas as pd
import numpy as np
import plotly.express as px

from dash import Dash, html, dcc, dash_table
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc

# -------------------------
# Rutas y configuración
# -------------------------
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

FN_NOFETAL = DATA_DIR / "NoFetal2019.xlsx"
FN_DIVIPOLA = DATA_DIR / "Divipola.xlsx"
FN_CODES = DATA_DIR / "CodigosDeMuerte.xlsx"
FN_GEOJSON = DATA_DIR / "colombia_departamentos.geojson"  # opcional para mapa coroplético

px.defaults.template = "plotly_white"
PAPER_BG = "#f8f9fa"
PLOT_BG = "#ffffff"

# -------------------------
# Lectura segura de archivos
# -------------------------
def safe_read_excel(path: Path):
    if path.exists():
        try:
            return pd.read_excel(path, engine="openpyxl")
        except Exception as e:
            print(f"[WARN] Error leyendo {path.name}: {e}")
            return pd.DataFrame()
    else:
        print(f"[WARN] No encontrado: {path}")
        return pd.DataFrame()

df_nofetal = safe_read_excel(FN_NOFETAL)
df_divipola = safe_read_excel(FN_DIVIPOLA)
df_codes = safe_read_excel(FN_CODES)

# -------------------------
# Normalizar columnas (robusto)
# -------------------------
def find_col(df, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None

# Normalize headers to str and strip
df_nofetal.columns = [str(c).strip() for c in df_nofetal.columns]
df_divipola.columns = [str(c).strip() for c in df_divipola.columns]
df_codes.columns = [str(c).strip() for c in df_codes.columns]

# detect columns
NOFETAL_cod_depto = find_col(df_nofetal, ["COD_DEPARTAMENTO", "COD_DPTO", "COD_DEPTO", "COD_DANE"])
NOFETAL_cod_mpio  = find_col(df_nofetal, ["COD_MUNICIPIO", "COD_MPIO", "COD_MUN"])
NOFETAL_sexo      = find_col(df_nofetal, ["SEXO"])
NOFETAL_mes       = find_col(df_nofetal, ["MES", "MES_NUM", "NUM_MES"])
NOFETAL_grupoedad = find_col(df_nofetal, ["GRUPO_EDAD1", "GRUPO_EDAD"])
NOFETAL_codmuerte = find_col(df_nofetal, ["COD_MUERTE", "COD_MUERTE_STR", "COD_CIE", "CAUSA"])

DIV_cod_depto = find_col(df_divipola, ["COD_DEPARTAMENTO", "COD_DPTO", "COD_DANE"])
DIV_cod_mpio  = find_col(df_divipola, ["COD_MUNICIPIO", "COD_MPIO"])
DIV_depto     = find_col(df_divipola, ["DEPARTAMENTO", "NOMBRE_DEPARTAMENTO", "NOMBRE_DPT"])
DIV_mpio      = find_col(df_divipola, ["MUNICIPIO", "NOMBRE_MUNICIPIO"])

CODES_code_col = find_col(df_codes, ["CÓDIGO","CODIGO","Código","Código_CIE","Código_CIE10","Unnamed: 0"])
CODES_name_col = find_col(df_codes, ["NOMBRE","NOMBRE_CAUSA","DESCRIPCION","NOMBRE_CIE","Descripcion","Nombre"])

# -------------------------
# Preparar dataframe principal
# -------------------------
df = df_nofetal.copy() if not df_nofetal.empty else pd.DataFrame()

# ensure key strings for merge
if NOFETAL_cod_depto and NOFETAL_cod_depto in df.columns:
    df["COD_DEPARTAMENTO_STR"] = df[NOFETAL_cod_depto].astype(str).str.strip().str.zfill(2)
else:
    df["COD_DEPARTAMENTO_STR"] = ""

if NOFETAL_cod_mpio and NOFETAL_cod_mpio in df.columns:
    df["COD_MUNICIPIO_STR"] = df[NOFETAL_cod_mpio].astype(str).str.strip().str.zfill(3)
else:
    df["COD_MUNICIPIO_STR"] = ""

# MES
if NOFETAL_mes and NOFETAL_mes in df.columns:
    df["MES_NUM"] = pd.to_numeric(df[NOFETAL_mes], errors="coerce").fillna(0).astype(int)
else:
    df["MES_NUM"] = df.get("MES", np.nan)
    df["MES_NUM"] = pd.to_numeric(df["MES_NUM"], errors="coerce").fillna(0).astype(int)

# SEXO
if NOFETAL_sexo and NOFETAL_sexo in df.columns:
    df["SEXO"] = df[NOFETAL_sexo].astype(str).str.strip().str.upper()
else:
    df["SEXO"] = "NO_INFO"

# GRUPO EDAD
if NOFETAL_grupoedad and NOFETAL_grupoedad in df.columns:
    df["GRUPO_EDAD1"] = df[NOFETAL_grupoedad].astype(str).str.strip()
else:
    df["GRUPO_EDAD1"] = df.get("GRUPO_EDAD1", "")

# COD CAUSA
if NOFETAL_codmuerte and NOFETAL_codmuerte in df.columns:
    df["COD_MUERTE_STR"] = df[NOFETAL_codmuerte].astype(str).str.strip().str.upper()
else:
    df["COD_MUERTE_STR"] = df.get("COD_MUERTE_STR", "").astype(str)

# -------------------------
# Merge con divipola para obtener nombres legibles
# -------------------------
if all([DIV_cod_depto, DIV_cod_mpio, DIV_depto, DIV_mpio]):
    # normalizar divipola keys
    df_divipola[DIV_cod_depto] = df_divipola[DIV_cod_depto].astype(str).str.strip().str.zfill(2)
    df_divipola[DIV_cod_mpio] = df_divipola[DIV_cod_mpio].astype(str).str.strip().str.zfill(3)
    df = df.merge(
        df_divipola[[DIV_cod_depto, DIV_cod_mpio, DIV_depto, DIV_mpio]],
        left_on=["COD_DEPARTAMENTO_STR","COD_MUNICIPIO_STR"],
        right_on=[DIV_cod_depto, DIV_cod_mpio],
        how="left",
        suffixes=("","_DIV")
    )
    df["DEPARTAMENTO"] = df[DIV_depto].fillna("Departamento desconocido")
    df["MUNICIPIO"] = df[DIV_mpio].fillna("Municipio desconocido")
else:
    # fallback: intentar columnas ya presentes
    if "DEPARTAMENTO" not in df.columns:
        df["DEPARTAMENTO"] = df.get("DEPARTAMENTO", "Departamento desconocido")
    if "MUNICIPIO" not in df.columns:
        df["MUNICIPIO"] = df.get("MUNICIPIO", "Municipio desconocido")

# -------------------------
# Mapear nombres de causa
# -------------------------
code_map = {}
if not df_codes.empty and CODES_code_col and CODES_name_col and CODES_code_col in df_codes.columns and CODES_name_col in df_codes.columns:
    df_codes[CODES_code_col] = df_codes[CODES_code_col].astype(str).str.strip().str.upper()
    df_codes[CODES_name_col] = df_codes[CODES_name_col].astype(str).str.strip()
    code_map = dict(df_codes[[CODES_code_col, CODES_name_col]].dropna().values)
# helper
def map_cause(code):
    if not code or pd.isna(code) or str(code).strip()=="":
        return "DESCONOCIDO"
    return code_map.get(str(code).strip().upper(), str(code).strip())

df["CAUSA_NOMBRE"] = df["COD_MUERTE_STR"].map(map_cause)

# -------------------------
# Mapear GRUPO_EDAD1 a etiquetas legibles
# -------------------------
age_map = {
    '0':'Mortalidad neonatal 0-4','1':'Mortalidad neonatal 0-4','2':'Mortalidad neonatal 0-4','3':'Mortalidad neonatal 0-4','4':'Mortalidad neonatal 0-4',
    '5':'Mortalidad infantil 1-11 meses','6':'Mortalidad infantil 1-11 meses',
    '7':'Primera infancia 1-4','8':'Primera infancia 1-4',
    '9':'Niñez 5-14','10':'Niñez 5-14',
    '11':'Adolescencia 15-19',
    '12':'Juventud 20-29','13':'Juventud 20-29',
    '14':'Adultez temprana 30-44','15':'Adultez temprana 30-44','16':'Adultez temprana 30-44',
    '17':'Adultez intermedia 45-59','18':'Adultez intermedia 45-59','19':'Adultez intermedia 45-59',
    '20':'Vejez 60-84','21':'Vejez 60-84','22':'Vejez 60-84','23':'Vejez 60-84','24':'Vejez 60-84',
    '25':'Longevidad 85+','26':'Longevidad 85+','27':'Longevidad 85+','28':'Longevidad 85+',
    '29':'Edad desconocida / Sin información'
}
def map_age(code):
    try:
        k = str(int(float(code)))
    except:
        k = str(code).strip()
    return age_map.get(k, 'Sin info')
df["GRUPO_EDAD_LABEL"] = df["GRUPO_EDAD1"].apply(map_age)

# -------------------------
# Agregados iniciales (para mostrar sin filtro)
# -------------------------
muertes_depto = df.groupby("DEPARTAMENTO").size().reset_index(name="TOTAL_MUERTES").sort_values("TOTAL_MUERTES", ascending=False)
muertes_mes = df.groupby("MES_NUM").size().reset_index(name="TOTAL_MUERTES").sort_values("MES_NUM")
cities_low10 = df.groupby("MUNICIPIO").size().reset_index(name="TOTAL_MUERTES").sort_values("TOTAL_MUERTES", ascending=True).head(10)
homicidios = df[df["COD_MUERTE_STR"].str.contains(r'X9[0-9]|X95|X9', na=False)]
top_5_homicidios = homicidios.groupby("MUNICIPIO").size().reset_index(name="TOTAL_HOMICIDIOS").sort_values("TOTAL_HOMICIDIOS", ascending=False).head(5)
stacked = df.groupby(["DEPARTAMENTO","SEXO"]).size().reset_index(name="TOTAL_MUERTES")
df_top_causas = df.groupby(["COD_MUERTE_STR","CAUSA_NOMBRE"]).size().reset_index(name="TOTAL").sort_values("TOTAL", ascending=False).head(10)

# -------------------------
# Cargar geojson si existe (opcional)
# -------------------------
geojson = None
geo_prop = None
if FN_GEOJSON.exists():
    try:
        with open(FN_GEOJSON, "r", encoding="utf-8") as f:
            geojson = json.load(f)
        # try detect name property
        if "features" in geojson and len(geojson["features"])>0:
            props = list(geojson["features"][0].get("properties", {}).keys())
            for c in ["NOMBRE_DPT","NOMBRE","NOMBRE_DEPART","departamento","name"]:
                if c in props:
                    geo_prop = c
                    break
            if geo_prop is None:
                for p in props:
                    if isinstance(geojson["features"][0]["properties"].get(p), str):
                        geo_prop = p
                        break
    except Exception as e:
        print("[WARN] Error leyendo GeoJSON:", e)
        geojson = None

# -------------------------
# DASH app
# -------------------------
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server  # exportable para gunicorn

dept_options = [{"label": d, "value": d} for d in sorted(df["DEPARTAMENTO"].fillna("Departamento desconocido").unique())]

app.layout = dbc.Container([
    html.H1("Análisis Mortalidad Colombia - 2019", className="text-center mt-3 mb-3"),
    dbc.Row([
        dbc.Col([
            html.Div([
                html.Label("Filtrar por Departamento"),
                dcc.Dropdown(id="dept-dropdown",
                             options=[{"label":"Todos","value":"_ALL_"}]+dept_options,
                             value="_ALL_", clearable=False),
                html.Br(),
                html.Div(id="geo-msg", style={"color":"#8a2b2b"})
            ], style={"background":PAPER_BG, "padding":"12px", "borderRadius":"8px"}),
            html.Br(),
            dbc.Card(dbc.CardBody([
                html.H5("Resumen rápido"),
                html.P(f"Registros totales: {len(df):,}"),
                html.P(f"Departamentos detectados: {df['DEPARTAMENTO'].nunique():,}"),
                html.P(f"Municipios detectados: {df['MUNICIPIO'].nunique():,}")
            ]))
        ], width=3),
        dbc.Col([
            dcc.Tabs([
                dcc.Tab(label="Mapa: Muertes por Departamento", children=[dcc.Graph(id="map-fig")]),
                dcc.Tab(label="Muertes por Mes", children=[dcc.Graph(id="fig-mes")]),
                dcc.Tab(label="Ciudades Más Violentas (homicidios)", children=[dcc.Graph(id="fig-homicidios")]),
                dcc.Tab(label="Ciudades con Menor Mortalidad (10)", children=[dcc.Graph(id="fig-low10")]),
                dcc.Tab(label="Muertes por Sexo (apilado)", children=[dcc.Graph(id="fig-stack")]),
                dcc.Tab(label="Distribución por Edad", children=[dcc.Graph(id="fig-hist")]),
                dcc.Tab(label="Top 10 Causas", children=[
                    dash_table.DataTable(
                        id="table-top-causas",
                        data=df_top_causas.to_dict("records"),
                        columns=[{"name":"Código","id":"COD_MUERTE_STR"},
                                 {"name":"Nombre de la causa","id":"CAUSA_NOMBRE"},
                                 {"name":"Total","id":"TOTAL"}],
                        page_size=10,
                        style_table={"overflowX":"auto"},
                        style_header={"backgroundColor":"#0d6efd","color":"white","fontWeight":"bold"},
                        style_cell={"textAlign":"center"}
                    )
                ])
            ])
        ], width=9)
    ])
], fluid=True)

# -------------------------
# Callback principal (reconstruye figuras según filtro)
# -------------------------
@app.callback(
    Output("geo-msg","children"),
    Output("map-fig","figure"),
    Output("fig-mes","figure"),
    Output("fig-homicidios","figure"),
    Output("fig-low10","figure"),
    Output("fig-stack","figure"),
    Output("fig-hist","figure"),
    Output("table-top-causas","data"),
    Input("dept-dropdown","value")
)
def update_all(selected_dept):
    dff = df.copy()
    if selected_dept and selected_dept != "_ALL_":
        dff = dff[dff["DEPARTAMENTO"] == selected_dept]

    geo_message = ""
    # MAPA: usar geojson si está (choropleth) o fallback a barras
    if geojson is not None and geo_prop:
        dept_counts = dff.groupby("DEPARTAMENTO").size().reset_index(name="TOTAL_MUERTES")
        try:
            fig_map = px.choropleth_mapbox(
                dept_counts,
                geojson=geojson,
                locations="DEPARTAMENTO",
                color="TOTAL_MUERTES",
                featureidkey=f"properties.{geo_prop}",
                hover_name="DEPARTAMENTO",
                hover_data={"TOTAL_MUERTES":True},
                mapbox_style="carto-positron",
                center={"lat":4.6,"lon":-74.08},
                zoom=4.2,
                opacity=0.7,
                color_continuous_scale="OrRd",
                title="Muertes por Departamento - 2019"
            )
            fig_map.update_layout(margin={"r":0,"t":30,"l":0,"b":0}, height=520, paper_bgcolor=PAPER_BG, plot_bgcolor=PLOT_BG)
        except Exception as e:
            geo_message = f"GeoJSON presente pero no se pudo graficar: {e}. Se muestra alternativa."
            fig_map = px.bar(muertes_depto.head(30), x="DEPARTAMENTO", y="TOTAL_MUERTES", title="Muertes por Departamento (Top 30)")
            fig_map.update_layout(height=450, paper_bgcolor=PAPER_BG)
    else:
        if not FN_GEOJSON.exists():
            geo_message = "No se encontró 'data/colombia_departamentos.geojson' (opcional). Mostrando barras."
        else:
            geo_message = "GeoJSON presente pero no detectada propiedad de nombre. Mostrando barras."
        fig_map = px.bar(muertes_depto.head(30), x="DEPARTAMENTO", y="TOTAL_MUERTES", title="Muertes por Departamento (Top 30)")
        fig_map.update_layout(height=450, paper_bgcolor=PAPER_BG)

    # MUERTES POR MES
    mm = dff.groupby("MES_NUM").size().reset_index(name="TOTAL_MUERTES").sort_values("MES_NUM")
    if mm["MES_NUM"].nunique() == 0:
        fig_mes = px.line(pd.DataFrame({"MES_NUM":[0], "TOTAL_MUERTES":[0]}), x="MES_NUM", y="TOTAL_MUERTES", title="Muertes por Mes - sin datos")
    else:
        fig_mes = px.line(mm, x="MES_NUM", y="TOTAL_MUERTES", markers=True, title="Muertes por Mes - 2019", line_shape="spline")
        fig_mes.update_layout(xaxis=dict(tickmode="linear", tick0=1, dtick=1))
    fig_mes.update_layout(height=350, paper_bgcolor=PAPER_BG)

    # HOMICIDIOS - top 5 (X9x)
    hom = dff[dff["COD_MUERTE_STR"].str.contains(r'X9[0-9]|X95|X9', na=False)]
    top_h = hom.groupby("MUNICIPIO").size().reset_index(name="TOTAL_HOMICIDIOS").sort_values("TOTAL_HOMICIDIOS", ascending=False).head(5)
    if top_h.empty:
        fig_hom = px.bar(pd.DataFrame({"MUNICIPIO":["Sin datos"], "TOTAL_HOMICIDIOS":[0]}), x="MUNICIPIO", y="TOTAL_HOMICIDIOS", title="5 Ciudades Más Violentas (sin datos X9x)")
    else:
        fig_hom = px.bar(top_h, x="MUNICIPIO", y="TOTAL_HOMICIDIOS", color="TOTAL_HOMICIDIOS", title="5 Ciudades Más Violentas (Códigos X9x)", color_continuous_scale="Reds")
    fig_hom.update_layout(height=350, paper_bgcolor=PAPER_BG)

    # CIUDADES CON MENOR MORTALIDAD (10)
    low10 = dff.groupby("MUNICIPIO").size().reset_index(name="TOTAL_MUERTES").sort_values("TOTAL_MUERTES", ascending=True).head(10)
    if low10.empty:
        fig_low10 = px.pie(pd.DataFrame({"MUNICIPIO":["Sin datos"], "TOTAL_MUERTES":[1]}), names="MUNICIPIO", values="TOTAL_MUERTES", title="10 Ciudades con Menor Mortalidad")
    else:
        fig_low10 = px.pie(low10, names="MUNICIPIO", values="TOTAL_MUERTES", title="10 Ciudades con Menor Mortalidad")
    fig_low10.update_layout(height=350, paper_bgcolor=PAPER_BG)

    # BARRAS APILADAS POR SEXO
    st = dff.groupby(["DEPARTAMENTO","SEXO"]).size().reset_index(name="TOTAL_MUERTES")
    if st.empty:
        fig_stack = px.bar(pd.DataFrame({"DEPARTAMENTO":["Sin datos"], "TOTAL_MUERTES":[0], "SEXO":["N/A"]}), x="DEPARTAMENTO", y="TOTAL_MUERTES", color="SEXO", title="Muertes por Sexo")
    else:
        fig_stack = px.bar(st, x="DEPARTAMENTO", y="TOTAL_MUERTES", color="SEXO", title="Muertes por Sexo en Cada Departamento")
    fig_stack.update_layout(barmode="stack", height=450, paper_bgcolor=PAPER_BG)

    # HISTOGRAMA / DISTRIBUCIÓN POR EDAD
    hist_df = dff.groupby("GRUPO_EDAD_LABEL").size().reset_index(name="TOTAL").sort_values("TOTAL", ascending=False)
    if hist_df.empty:
        fig_hist = px.bar(pd.DataFrame({"GRUPO_EDAD_LABEL":["Sin datos"], "TOTAL":[0]}), x="GRUPO_EDAD_LABEL", y="TOTAL", title="Distribución por Grupo de Edad")
    else:
        fig_hist = px.bar(hist_df, x="GRUPO_EDAD_LABEL", y="TOTAL", title="Distribución de Muertes por Grupo de Edad")
        fig_hist.update_layout(xaxis_tickangle=-45)
    fig_hist.update_layout(height=400, paper_bgcolor=PAPER_BG)

    # TABLA TOP 10 CAUSAS (según filtro)
    top_c = dff.groupby(["COD_MUERTE_STR","CAUSA_NOMBRE"]).size().reset_index(name="TOTAL").sort_values("TOTAL", ascending=False).head(10)
    table_data = top_c.to_dict("records")

    # aplicar fondo consistente
    for f in (fig_map, fig_mes, fig_hom, fig_low10, fig_stack, fig_hist):
        try:
            f.update_layout(plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG)
        except Exception:
            pass

    return geo_message, fig_map, fig_mes, fig_hom, fig_low10, fig_stack, fig_hist, table_data

# -------------------------
# Run (para desarrollo local y PaaS)
# -------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    # en Render es preferible ejecutar con gunicorn: 'gunicorn app:server'
    # pero para pruebas locales:
    app.run(host="0.0.0.0", port=10000, debug=False)
