# src/ui/ui_components.py
import streamlit as st
import pandas as pd
from src.config.config_settings import SQL_SCHEMA
from src.services.services_gpt import GPTService
from src.services.services_pdf import PDFService
from src.services.services_data import DataService

def render_upload():
   st.header("Upload de Currículos")
   
   arquivos = st.file_uploader(
        "Selecione os PDFs dos currículos",
        type="pdf",
       accept_multiple_files=True
   )
   
   if arquivos:
       gpt_service = GPTService()
       pdf_service = PDFService()
       data_service = DataService()
       
       for arquivo in arquivos:
           with st.spinner(f'Processando {arquivo.name}...'):
               try:
                   texto_pdf = pdf_service.extrair_texto(arquivo)
                   dados = gpt_service.analisar_curriculo(texto_pdf)
                   data_service.salvar_candidato(dados, texto_pdf)
                   st.success(f"✅ {arquivo.name} processado com sucesso")
               except Exception as e:
                   st.error(f"❌ Erro ao processar {arquivo.name}: {e}")

def render_viewer():
   st.header("Dados dos Candidatos")
   
   try:
       data_service = DataService()
       dados = data_service.buscar_candidatos()
       if dados:
           df = pd.DataFrame(dados)
           st.dataframe(df)
       else:
           st.info("Nenhum dado encontrado")
   except Exception as e:
       st.error(f"Erro ao carregar dados: {e}")

def render_query():
   st.header("Consultas Personalizadas")
   
   prompt = st.text_area("Digite sua consulta:", height=100)
   if st.button("Consultar"):
       try:
           gpt_service = GPTService()
           data_service = DataService()
           
           schema = "Considere a tabela a seguir: " + SQL_SCHEMA
           
           query = gpt_service.gerar_query_sql(prompt, schema)
           if query:
               st.code(query, language="sql")
               resultados = data_service.executar_query(query)
               
               if resultados:
                   df = pd.DataFrame(resultados)
                   st.dataframe(df)
               else:
                   st.info("Nenhum resultado encontrado")
       except Exception as e:
           st.error(f"Erro na consulta: {e}")