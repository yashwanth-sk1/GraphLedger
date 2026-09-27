#!/usr/bin/env bash
set -e
python3 -m pip install -r requirements.txt
python3 generate_data.py
streamlit run app.py
