import streamlit as st

# Configurações do OpenAI
OPENAI_KEY = st.secrets["openai_key"]

# Configurações do Banco de Dados
DB_CONFIG = {
    'host': st.secrets["mysql_host"],
    'user': st.secrets["mysql_user"],
    'password': st.secrets["mysql_password"],
    'database': st.secrets["mysql_database"],
    'port': st.secrets.get("mysql_port", 3306),
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci',
    'pool_size': 5,
    'pool_name': 'mypool',
    'pool_reset_session': True
}

# Schema do Banco de Dados
# Schema do Banco de Dados
SQL_SCHEMA = """
-- Tabela de Gêneros
CREATE TABLE IF NOT EXISTS generos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(50),
    descricao TEXT,
    data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabela de Profissões
CREATE TABLE IF NOT EXISTS profissoes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(255),
    descricao TEXT,
    data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabela de Áreas de Interesse
CREATE TABLE IF NOT EXISTS areas_interesse (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(255),
    descricao TEXT,
    data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabela de Áreas de Atuação
CREATE TABLE IF NOT EXISTS areas_atuacao (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(255),
    descricao TEXT,
    data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabela de Faculdades
CREATE TABLE IF NOT EXISTS faculdades (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(255),
    cidade VARCHAR(255),
    estado VARCHAR(255),
    pais VARCHAR(255),
    tipo VARCHAR(50),  -- pública, privada, etc
    ranking INT,       -- posição em rankings
    data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabela de Idiomas
CREATE TABLE IF NOT EXISTS idiomas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(255),
    codigo VARCHAR(5),
    data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabela Principal de Profissionais
CREATE TABLE IF NOT EXISTS profissionais (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(255),
    email VARCHAR(255),
    telefone VARCHAR(50),
    endereco TEXT,
    portfolio_url VARCHAR(255),
    linkedin_url VARCHAR(255),
    github_url VARCHAR(255),
    profissao_id INT,
    faculdade_id INT,
    genero_id INT,
    idioma_principal_id INT,
    nivel_idioma_principal VARCHAR(50),
    pdf_curriculo LONGTEXT,
    idade INT,
    pretensao_salarial DECIMAL(10,2),
    disponibilidade VARCHAR(50),
    tipo_contrato VARCHAR(50),
    data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
    ultima_atualizacao DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    observacoes_ia JSON,
    campos_dinamicos JSON,
    FOREIGN KEY (profissao_id) REFERENCES profissoes(id),
    FOREIGN KEY (faculdade_id) REFERENCES faculdades(id),
    FOREIGN KEY (genero_id) REFERENCES generos(id),
    FOREIGN KEY (idioma_principal_id) REFERENCES idiomas(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabela de Relacionamento Profissionais-Idiomas
CREATE TABLE IF NOT EXISTS profissionais_idiomas (
    profissional_id INT,
    idioma_id INT,
    nivel VARCHAR(50),
    certificacao VARCHAR(255),
    data_certificacao DATE,
    data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (profissional_id, idioma_id),
    FOREIGN KEY (profissional_id) REFERENCES profissionais(id),
    FOREIGN KEY (idioma_id) REFERENCES idiomas(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabela de Relacionamento Profissionais-Áreas de Interesse
CREATE TABLE IF NOT EXISTS profissionais_areas_interesse (
    profissional_id INT,
    area_interesse_id INT,
    nivel_interesse INT,  -- 1 a 5
    data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (profissional_id, area_interesse_id),
    FOREIGN KEY (profissional_id) REFERENCES profissionais(id),
    FOREIGN KEY (area_interesse_id) REFERENCES areas_interesse(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabela de Relacionamento Profissionais-Áreas de Atuação
CREATE TABLE IF NOT EXISTS profissionais_areas_atuacao (
    profissional_id INT,
    area_atuacao_id INT,
    anos_experiencia FLOAT,
    ultimo_cargo VARCHAR(255),
    ultima_empresa VARCHAR(255),
    data_inicio DATE,
    data_fim DATE,
    descricao_atividades TEXT,
    data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (profissional_id, area_atuacao_id),
    FOREIGN KEY (profissional_id) REFERENCES profissionais(id),
    FOREIGN KEY (area_atuacao_id) REFERENCES areas_atuacao(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Inserir valores padrão na tabela de gêneros
INSERT INTO generos (nome, descricao) 
SELECT * FROM (
    SELECT 'masculino' as nome, 'Gênero masculino' as descricao
    UNION ALL
    SELECT 'feminino', 'Gênero feminino'
    UNION ALL
    SELECT 'não identificado', 'Gênero não identificado'
) AS tmp
WHERE NOT EXISTS (
    SELECT 1 FROM generos
) LIMIT 1;
"""

# Constantes do Sistema
NIVEIS_IDIOMA = ['básico', 'intermediário', 'avançado', 'fluente']
TIPOS_CONTRATO = ['clt', 'pj', 'freelancer', 'estágio', 'temporário']
DISPONIBILIDADE = ['imediata', '15 dias', '30 dias', '45 dias', 'a combinar']
NIVEIS_INTERESSE = [(1, 'muito baixo'), (2, 'baixo'), (3, 'médio'), (4, 'alto'), (5, 'muito alto')]

# Configurações de Cache
CACHE_CONFIG = {
    'CACHE_TYPE': 'SimpleCache',
    'CACHE_DEFAULT_TIMEOUT': 300,
    'CACHE_THRESHOLD': 500
}

# Configurações de Logging
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
    },
    'handlers': {
        'default': {
            'level': 'INFO',
            'formatter': 'standard',
            'class': 'logging.StreamHandler',
        },
        'file': {
            'level': 'INFO',
            'formatter': 'standard',
            'class': 'logging.FileHandler',
            'filename': 'app.log',
            'mode': 'a',
        }
    },
    'loggers': {
        '': {
            'handlers': ['default', 'file'],
            'level': 'INFO',
            'propagate': True
        }
    }
}

# Templates para o GPT
TEMPLATE_ANALISE_CURRICULO = """
Analise o currículo fornecido e extraia as seguintes informações:
- Dados básicos (nome, email, gênero, idade)
- Profissão atual
- Formação acadêmica
- Experiência profissional
- Idiomas e níveis
- Áreas de interesse
- Informações de contato
- Observações relevantes

Retorne os dados no formato JSON especificado.
"""

TEMPLATE_QUERY_SQL = """
Gere uma query SQL otimizada seguindo as melhores práticas:
- Use JOINs apropriados
- Considere índices
- Trate textos em lowercase
- Use aliases claros
"""

# Configurações de Interface
UI_CONFIG = {
    'max_file_size': 5 * 1024 * 1024,  # 5MB
    'allowed_file_types': ['pdf'],
    'max_files_upload': 10,
    'timeout_seconds': 300,
    'theme': {
        'primaryColor': '#FF4B4B',
        'backgroundColor': '#FFFFFF',
        'secondaryBackgroundColor': '#F0F2F6',
        'textColor': '#262730',
        'font': 'sans-serif'
    },
    'page_icon': '📄',
    'layout': 'wide',
    'sidebar_state': 'expanded'
}

# Configurações de Segurança
SECURITY_CONFIG = {
    'password_min_length': 8,
    'password_require_upper': True,
    'password_require_lower': True,
    'password_require_number': True,
    'password_require_special': True,
    'session_lifetime': 3600,  # 1 hora
    'max_login_attempts': 3,
    'lockout_time': 300  # 5 minutos
}

# Configurações de Rate Limiting
RATE_LIMIT_CONFIG = {
    'default': '100/hour',
    'upload': '50/hour',
    'query': '200/hour'
}

# Configurações de Email
EMAIL_CONFIG = {
    'MAIL_SERVER': st.secrets.get("mail_server", "smtp.gmail.com"),
    'MAIL_PORT': st.secrets.get("mail_port", 587),
    'MAIL_USE_TLS': True,
    'MAIL_USERNAME': st.secrets.get("mail_username", ""),
    'MAIL_PASSWORD': st.secrets.get("mail_password", ""),
    'MAIL_DEFAULT_SENDER': st.secrets.get("mail_sender", "")
}

# Configurações de Integração
INTEGRATION_CONFIG = {
    'linkedin_api_key': st.secrets.get("linkedin_api_key", ""),
    'github_api_key': st.secrets.get("github_api_key", ""),
    'indeed_api_key': st.secrets.get("indeed_api_key", "")
}