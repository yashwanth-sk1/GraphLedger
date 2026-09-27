@echo off
python -m pip install -r requirements.txt
python generate_data.py
streamlit run app.py
pause
