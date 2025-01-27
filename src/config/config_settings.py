# src/config/config_settings.py
import streamlit as st

OPENAI_KEY = st.secrets["openai_key"]
DB_CONFIG = {
    'host': st.secrets["mysql_host"],
    'user': st.secrets["mysql_user"],
    'password': st.secrets["mysql_password"],
    'database': st.secrets["mysql_database"]
}

SQL_SCHEMA = """
    -- Tabela principal de candidatos
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
        ultima_experiencia TEXT,
        todas_experiencias TEXT,
        habilidades TEXT,
        linkedin VARCHAR(255),
        github VARCHAR(255),
        telefone VARCHAR(50),
        data_criacao DATETIME,
        pdf_conteudo LONGTEXT,
        observacoes_ia TEXT,
        campos_dinamicos TEXT,
        areas_interesse TEXT,
        areas_atuacao TEXT
    );

    -- Tabela de áreas (sem restrição UNIQUE)
    CREATE TABLE IF NOT EXISTS areas (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nome VARCHAR(255),
        tipo ENUM('interesse', 'atuacao'),
        data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
        total_uso INT DEFAULT 1,
        INDEX idx_nome_tipo (nome, tipo)
    );

    -- Tabela de relacionamento candidato-áreas
    CREATE TABLE IF NOT EXISTS candidato_areas (
        id INT AUTO_INCREMENT PRIMARY KEY,
        candidato_id INT,
        area_id INT,
        tipo ENUM('interesse', 'atuacao'),
        FOREIGN KEY (candidato_id) REFERENCES candidatos(id) ON DELETE CASCADE,
        FOREIGN KEY (area_id) REFERENCES areas(id) ON DELETE CASCADE,
        INDEX idx_candidato_area (candidato_id, area_id)
    );
"""