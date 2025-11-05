
# Mortalidad Colombia 2019 - Dashboard (Entrega para Actividad 4)

Integrantes:
- Aldo Giuliano Zabala Ruocco
- Jhony Barbosa
- Lucas Vélez Vélez

Descripción: Aplicación Dash + Plotly para analizar mortalidad en Colombia (2019). 
Contiene mapas, series temporales, tablas y gráficos interactivos.

Estructura del proyecto:
- app.py: aplicación Dash (principal)
- requirements.txt: librerías
- data/: archivos Excel originales
- assets/: estilos

Ejecución local:
1. python -m venv venv
2. venv\Scripts\Activate.ps1
3. pip install -r requirements.txt
4. python app.py
5. Abrir http://127.0.0.1:8050/

Despliegue en Render (resumen):
- Subir repo a GitHub
- Crear Web Service en Render
- Start command: gunicorn app:server
- Ensure requirements.txt is present

Checklist para 10/10:
- [ ] Todos los gráficos requeridos implementados y probados.
- [ ] Títulos, etiquetas, leyendas y colores adecuados.
- [ ] Filtros interactivos (departamento, sexo, grupo de edad).
- [ ] URL pública funcionando (Render) y GitHub repo con README y capturas.
- [ ] Informe con interpretaciones y capturas listo para entregar.

