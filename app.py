# app.py
import streamlit as st
from src.ui.ui_components import render_query,render_viewer,render_upload

st.set_page_config(page_title="Analisador de CVs", layout="wide")

def main():
    st.title("Analisador de Currículos")
    
    menu = st.sidebar.selectbox(
        "Escolha uma opção",
        ["Upload de CVs", "Visualizar Dados", "Consultas Personalizadas"]
    )
    
    if menu == "Upload de CVs":
        render_upload()
    elif menu == "Visualizar Dados":
        render_viewer()
    elif menu == "Consultas Personalizadas":
        render_query()

if __name__ == "__main__":
    main()