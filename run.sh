#!/bin/bash
# Ejecutar la app de Control Financiero
cd "$(dirname "$0")"

# Instalar dependencias si no están
pip3 install -q -r requirements.txt

# Lanzar Streamlit
streamlit run app.py --server.port 8501 --server.headless false
