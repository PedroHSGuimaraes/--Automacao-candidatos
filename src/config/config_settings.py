import streamlit as st
OPENAI_KEY = st.secrets["openai_key"]
DB_CONFIG = {
    'host': st.secrets["mysql_host"],
    'user': st.secrets["mysql_user"],
    'password': st.secrets["mysql_password"],
    'database': st.secrets["mysql_database"]
}

SQL_SCHEMA = """
    CREATE TABLE IF NOT EXISTS candidatos (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nome VARCHAR(255),
        email VARCHAR(255),
        genero VARCHAR(50),
        idade INT,
        instituto_formacao VARCHAR(255),
        curso VARCHAR(255),
        periodo VARCHAR(50),
        tempo_experiencia FLOAT,
        area_atuacao VARCHAR(255),
        ultima_experiencia TEXT,
        todas_experiencias TEXT,
        habilidades TEXT,
        linkedin VARCHAR(255),
        github VARCHAR(255),
        telefone VARCHAR(50),
        data_criacao DATETIME,
        pdf_conteudo LONGTEXT,
        observacoes_ia JSON,
        campos_dinamicos JSON
    )
"""