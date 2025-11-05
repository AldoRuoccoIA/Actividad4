# app.py
# Dash app para Análisis de Mortalidad No Fetal 2019
# Usa los archivos: NoFetal2019.xlsx, Divipola.xlsx, CodigosDeMuerte.xlsx (en carpeta data/)
# Recomendado: tener style.css en assets/ (Dash lo carga automáticamente)

import os
import json
from pathlib import Path

import pandas as pd
import numpy as np

from dash import Dash, html, dcc, dash_table
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px

# -------------------------
# Rutas y configuración
# -------------------------
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

FN_NOFETAL = DATA_DIR / "NoFetal2019.xlsx"
FN_DIVIPOLA = DATA_DIR / "Divipola.xlsx"
FN_CODES = DATA_DIR / "CodigosDeMuerte.xlsx"
FN_GEOJSON = DATA_DIR / "colombia_departamentos.geojson"

px.defaults.template = "plotly_white"
PAPER_BG = "#f8f9fa"
PLOT_BG = "#ffffff"

# -------------------------
# Cargar datos (seguro)
# -------------------------
def safe_read_excel(path):
    if path.exists():
        try:
            return pd.read_excel(path, engine="openpyxl")
        except Exception as e:
            print(f"Error leyendo {path.name}: {e}")
            return pd.DataFrame()
    else:
        print(f"No encontrado: {path}")
        return pd.DataFrame()

df_nofetal = safe_read_excel(FN_NOFETAL)
df_divipola = safe_read_excel(FN_DIVIPOLA)
df_codes = safe_read_excel(FN_CODES)

print("=== Columnas detectadas ===")
print("NoFetal:", list(df_nofetal.columns))
print("Divipola:", list(df_divipola.columns))
print("CodigosDeMuerte:", list(df_codes.columns))

# -------------------------
# Normalizar nombres de columnas
# -------------------------
df_nofetal.columns = [str(c).strip() for c in df_nofetal.columns]
df_divipola.columns = [str(c).strip() for c in df_divipola.columns]
df_codes.columns = [str(c).strip() for c in df_codes.columns]

# -------------------------
# Función auxiliar para detectar columnas
# -------------------------
def find_col(df, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None

NOFETAL_cod_depto = find_col(df_nofetal, ["COD_DEPARTAMENTO", "COD_DPTO", "COD_DEPTO", "COD_DANE"])
NOFETAL_cod_mpio  = find_col(df_nofetal, ["COD_MUNICIPIO", "COD_MPIO", "COD_MPIO_A", "COD_MUN"])
NOFETAL_sexo      = find_col(df_nofetal, ["SEXO"])
NOFETAL_mes       = find_col(df_nofetal, ["MES"])
NOFETAL_grupoedad = find_col(df_nofetal, ["GRUPO_EDAD1", "GRUPO_EDAD"])
NOFETAL_codmuerte = find_col(df_nofetal, ["COD_MUERTE", "COD_MUERTE", "COD_MUER"])

DIV_cod_depto = find_col(df_divipola, ["COD_DEPARTAMENTO", "COD_DEPTO", "COD_DANE"])
DIV_cod_mpio  = find_col(df_divipola, ["COD_MUNICIPIO", "COD_MPIO"])
DIV_depto     = find_col(df_divipola, ["DEPARTAMENTO", "NOMBRE_DEPARTAMENTO", "NOMBRE_DPT"])
DIV_mpio      = find_col(df_divipola, ["MUNICIPIO", "NOMBRE_MUNICIPIO"])

CODES_code_col = find_col(df_codes, ["CÓDIGO","CODIGO","Código","Código_CIE","Código_CIE10","Unnamed: 0"])
CODES_name_col = find_col(df_codes, ["NOMBRE","NOMBRE_CAUSA","DESCRIPCION","NOMBRE_CIE","Descripcion","Nombre"])

# -------------------------
# Preparar dataframe principal
# -------------------------
df = df_nofetal.copy()

if NOFETAL_cod_depto:
    df["COD_DEPARTAMENTO_STR"] = df[NOFETAL_cod_depto].astype(str).str.strip()
else:
    df["COD_DEPARTAMENTO_STR"] = ""

if NOFETAL_cod_mpio:
    df["COD_MUNICIPIO_STR"] = df[NOFETAL_cod_mpio].astype(str).str.strip()
else:
    df["COD_MUNICIPIO_STR"] = ""

if NOFETAL_mes and NOFETAL_mes in df.columns:
    df["MES_NUM"] = pd.to_numeric(df[NOFETAL_mes], errors="coerce").fillna(0).astype(int)
else:
    df["MES_NUM"] = 0

if NOFETAL_sexo and NOFETAL_sexo in df.columns:
    df["SEXO"] = df[NOFETAL_sexo].astype(str).str.strip()
else:
    df["SEXO"] = "No disponible"

if NOFETAL_grupoedad and NOFETAL_grupoedad in df.columns:
    df["GRUPO_EDAD1"] = df[NOFETAL_grupoedad].astype(str).str.strip()
else:
    df["GRUPO_EDAD1"] = ""

if NOFETAL_codmuerte and NOFETAL_codmuerte in df.columns:
    df["COD_MUERTE_STR"] = df[NOFETAL_codmuerte].astype(str).str.strip()
else:
    df["COD_MUERTE_STR"] = ""

# -------------------------
# Merge con DIVIPOLA
# -------------------------
if DIV_cod_depto and DIV_cod_mpio and DIV_depto and DIV_mpio:
    df_divipola[DIV_cod_depto] = df_divipola[DIV_cod_depto].astype(str).str.strip()
    df_divipola[DIV_cod_mpio] = df_divipola[DIV_cod_mpio].astype(str).str.strip()
    df = df.merge(
        df_divipola[[DIV_cod_depto, DIV_cod_mpio, DIV_depto, DIV_mpio]],
        left_on=["COD_DEPARTAMENTO_STR", "COD_MUNICIPIO_STR"],
        right_on=[DIV_cod_depto, DIV_cod_mpio],
        how="left",
        suffixes=("", "_DIV")
    )
    df["DEPARTAMENTO"] = df[DIV_depto].fillna("Departamento desconocido")
    df["MUNICIPIO"] = df[DIV_mpio].fillna("Municipio desconocido")
else:
    df["DEPARTAMENTO"] = "Departamento desconocido"
    df["MUNICIPIO"] = "Municipio desconocido"

# -------------------------
# Mapear nombres de causa
# -------------------------
if CODES_code_col and CODES_name_col and (CODES_code_col in df_codes.columns) and (CODES_name_col in df_codes.columns):
    df_codes[CODES_code_col] = df_codes[CODES_code_col].astype(str).str.strip()
    df_codes[CODES_name_col] = df_codes[CODES_name_col].astype(str).str.strip()
    df = df.merge(
        df_codes[[CODES_code_col, CODES_name_col]],
        left_on="COD_MUERTE_STR",
        right_on=CODES_code_col,
        how="left"
    )
    df["CAUSA_NOMBRE"] = df[CODES_name_col].fillna(df["COD_MUERTE_STR"])
else:
    df["CAUSA_NOMBRE"] = df["COD_MUERTE_STR"].replace("", "No clasificada")

# -------------------------
# Mapear GRUPO_EDAD1 a etiquetas legibles
# -------------------------
age_map = {
    '0':'Mortalidad neonatal 0-4',
    '1':'Mortalidad neonatal 0-4',
    '2':'Mortalidad neonatal 0-4',
    '3':'Mortalidad neonatal 0-4',
    '4':'Mortalidad neonatal 0-4',
    '5':'Mortalidad infantil 1-11 meses',
    '6':'Mortalidad infantil 1-11 meses',
    '7':'Primera infancia 1-4',
    '8':'Primera infancia 1-4',
    '9':'Niñez 5-14',
    '10':'Niñez 5-14',
    '11':'Adolescencia 15-19',
    '12':'Juventud 20-29',
    '13':'Juventud 20-29',
    '14':'Adultez temprana 30-44',
    '15':'Adultez temprana 30-44',
    '16':'Adultez temprana 30-44',
    '17':'Adultez intermedia 45-59',
    '18':'Adultez intermedia 45-59',
    '19':'Adultez intermedia 45-59',
    '20':'Vejez 60-84',
    '21':'Vejez 60-84',
    '22':'Vejez 60-84',
    '23':'Vejez 60-84',
    '24':'Vejez 60-84',
    '25':'Longevidad 85+',
    '26':'Longevidad 85+',
    '27':'Longevidad 85+',
    '28':'Longevidad 85+',
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
# DASH APP
# -------------------------
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

dept_options = [{'label': d, 'value': d} for d in sorted(df['DEPARTAMENTO'].fillna("Departamento desconocido").unique())]

app.layout = dbc.Container([
    html.H1("Análisis Mortalidad Colombia - 2019", className="text-center mt-4 mb-3"),
    dbc.Row([
        dbc.Col([
            html.Div([
                html.Label("Filtrar por Departamento"),
                dcc.Dropdown(
                    id="dept-dropdown",
                    options=[{"label":"Todos","value":"_ALL_"}] + dept_options,
                    value="_ALL_",
                    clearable=False
                ),
                html.Br(),
                html.Div(id="geo-msg", style={"color":"#8a2b2b"})
            ], style={"background":PAPER_BG, "padding":"12px", "borderRadius":"8px", "boxShadow":"0 2px 6px rgba(0,0,0,0.03)"}),
            html.Br(),
            dbc.Card([
                dbc.CardBody([
                    html.H5("Resumen rápido", className="card-title"),
                    html.P(f"Registros totales: {len(df):,}"),
                    html.P(f"Departamentos detectados: {df['DEPARTAMENTO'].nunique()}"),
                    html.P(f"Municipios detectados: {df['MUNICIPIO'].nunique()}")
                ])
            ])
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
                        columns=[
                            {"name":"Código","id":"COD_MUERTE_STR"},
                            {"name":"Nombre de la causa","id":"CAUSA_NOMBRE"},
                            {"name":"Total","id":"TOTAL"}
                        ],
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
# Callback principal
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

    # MAPA (degradado en caso sin geojson)
    muertes_depto = dff.groupby("DEPARTAMENTO").size().reset_index(name="TOTAL_MUERTES")
    fig_map = px.bar(muertes_depto, x="DEPARTAMENTO", y="TOTAL_MUERTES", title="Muertes por Departamento (Top)")
    fig_map.update_layout(paper_bgcolor=PAPER_BG)

    # MUERTES POR MES
    mm = dff.groupby("MES_NUM").size().reset_index(name="TOTAL_MUERTES")
    fig_mes = px.line(mm, x="MES_NUM", y="TOTAL_MUERTES", markers=True, title="Muertes por Mes")
    fig_mes.update_layout(paper_bgcolor=PAPER_BG)

    # HOMICIDIOS
    hom = dff[dff["COD_MUERTE_STR"].str.contains(r'X9[0-9]|X95|X9', na=False)]
    top_h = hom.groupby("MUNICIPIO").size().reset_index(name="TOTAL_HOMICIDIOS").sort_values("TOTAL_HOMICIDIOS", ascending=False).head(5)
    fig_homicidios = px.bar(top_h, x="MUNICIPIO", y="TOTAL_HOMICIDIOS", title="Ciudades Más Violentas")
    fig_homicidios.update_layout(paper_bgcolor=PAPER_BG)

    # CIUDADES CON MENOR MORTALIDAD
    low10 = dff.groupby("MUNICIPIO").size().reset_index(name="TOTAL_MUERTES").sort_values("TOTAL_MUERTES").head(10)
    fig_low10 = px.pie(low10, names="MUNICIPIO", values="TOTAL_MUERTES", title="10 Ciudades con Menor Mortalidad")
    fig_low10.update_layout(paper_bgcolor=PAPER_BG)

    # SEXO
    st = dff.groupby(["DEPARTAMENTO","SEXO"]).size().reset_index(name="TOTAL_MUERTES")
    fig_stack = px.bar(st, x="DEPARTAMENTO", y="TOTAL_MUERTES", color="SEXO", title="Muertes por Sexo")
    fig_stack.update_layout(barmode="stack", paper_bgcolor=PAPER_BG)

    # HISTOGRAMA DE EDAD
    hist_df = dff.groupby("GRUPO_EDAD_LABEL").size().reset_index(name="TOTAL")
    fig_hist = px.bar(hist_df, x="GRUPO_EDAD_LABEL", y="TOTAL", title="Distribución por Grupo de Edad")
    fig_hist.update_layout(paper_bgcolor=PAPER_BG)

    # TABLA TOP CAUSAS
    top_c = dff.groupby(["COD_MUERTE_STR","CAUSA_NOMBRE"]).size().reset_index(name="TOTAL").sort_values("TOTAL", ascending=False).head(10)
    return "", fig_map, fig_mes, fig_homicidios, fig_low10, fig_stack, fig_hist, top_c.to_dict("records")

# -------------------------
# Run
# -------------------------
if __name__ == "__main__":
    app.run(debug=True, port=8050)
