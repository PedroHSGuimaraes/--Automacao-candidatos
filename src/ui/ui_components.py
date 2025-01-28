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
                    data_service.salvar_profissional(dados, texto_pdf)
                    st.success(f"✅ {arquivo.name} processado com sucesso")
                except Exception as e:
                    st.error(f"❌ Erro ao processar {arquivo.name}: {e}")


def render_viewer():
    st.header("Visualização dos Profissionais")

    # Filtros
    col1, col2, col3 = st.columns(3)

    with col1:
        nome_filtro = st.text_input("Filtrar por nome:")
    with col2:
        profissao_filtro = st.text_input("Filtrar por profissão:")
    with col3:
        area_filtro = st.text_input("Filtrar por área de atuação:")

    filtros = {}
    if nome_filtro:
        filtros['nome'] = nome_filtro
    if profissao_filtro:
        filtros['profissao'] = profissao_filtro
    if area_filtro:
        filtros['area_atuacao'] = area_filtro

    try:
        data_service = DataService()
        dados = data_service.buscar_profissionais(filtros)

        if dados:
            # Converter dados para DataFrame
            df = pd.DataFrame(dados)

            # Exibir métricas
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total de Profissionais", len(df))
            with col2:
                st.metric("Profissões Únicas", df['profissao'].nunique())
            with col3:
                st.metric("Idade Média", round(df['idade'].mean(), 1))
            with col4:
                st.metric("Áreas de Atuação", df['areas_atuacao'].nunique())

            # Exibir tabela detalhada
            st.dataframe(df)

            # Gráficos
            col1, col2 = st.columns(2)
            with col1:
                profissoes_count = df['profissao'].value_counts()
                st.bar_chart(profissoes_count)
                st.caption("Distribuição de Profissões")

            with col2:
                areas_count = df['areas_atuacao'].str.split(',').explode().value_counts()
                st.bar_chart(areas_count)
                st.caption("Áreas de Atuação mais Comuns")

        else:
            st.info("Nenhum profissional encontrado com os filtros aplicados")

    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")


def render_query():
    st.header("Consultas Personalizadas")

    # Mostrar estrutura do banco na sidebar
    st.sidebar.subheader("Estrutura do Banco de Dados")

    # Tabelas principais com suas colunas
    tabelas = {
        "profissionais": {
            "descrição": "Tabela principal com dados dos profissionais",
            "colunas": [
                "id", "nome", "email", "telefone", "endereco", "portfolio_url",
                "linkedin_url", "github_url", "profissao_id", "faculdade_id",
                "genero_id", "idioma_principal_id", "nivel_idioma_principal",
                "idade", "pretensao_salarial", "disponibilidade", "tipo_contrato"
            ]
        },
        "profissoes": {
            "descrição": "Cadastro de profissões",
            "colunas": ["id", "nome", "descricao"]
        },
        "generos": {
            "descrição": "Tipos de gênero",
            "colunas": ["id", "nome", "descricao"]
        },
        "faculdades": {
            "descrição": "Cadastro de instituições de ensino",
            "colunas": ["id", "nome", "cidade", "estado", "pais", "tipo", "ranking"]
        },
        "idiomas": {
            "descrição": "Cadastro de idiomas",
            "colunas": ["id", "nome", "codigo"]
        },
        "areas_interesse": {
            "descrição": "Áreas de interesse profissional",
            "colunas": ["id", "nome", "descricao"]
        },
        "areas_atuacao": {
            "descrição": "Áreas de atuação profissional",
            "colunas": ["id", "nome", "descricao"]
        }
    }

    # Tabelas de relacionamento
    relacionamentos = {
        "profissionais_idiomas": {
            "descrição": "Relaciona profissionais e seus idiomas",
            "colunas": ["profissional_id", "idioma_id", "nivel", "certificacao"]
        },
        "profissionais_areas_interesse": {
            "descrição": "Relaciona profissionais e suas áreas de interesse",
            "colunas": ["profissional_id", "area_interesse_id", "nivel_interesse"]
        },
        "profissionais_areas_atuacao": {
            "descrição": "Relaciona profissionais e suas áreas de atuação",
            "colunas": [
                "profissional_id", "area_atuacao_id", "anos_experiencia",
                "ultimo_cargo", "ultima_empresa", "descricao_atividades"
            ]
        }
    }

    # Exibir tabelas e colunas na sidebar
    tabelas_expander = st.sidebar.expander("Tabelas Principais")
    with tabelas_expander:
        for nome, info in tabelas.items():
            st.write(f"**{nome}**")
            st.write(f"_{info['descrição']}_")
            st.write("Colunas:")
            st.code(", ".join(info['colunas']))
            st.write("---")

    relacionamentos_expander = st.sidebar.expander("Tabelas de Relacionamento")
    with relacionamentos_expander:
        for nome, info in relacionamentos.items():
            st.write(f"**{nome}**")
            st.write(f"_{info['descrição']}_")
            st.write("Colunas:")
            st.code(", ".join(info['colunas']))
            st.write("---")

    # Exemplos de consultas mais completos
    st.subheader("Exemplos de Consultas")
    exemplos = {
        "Profissionais por Área": {
            "descrição": "Profissionais que atuam com desenvolvimento",
            "query": "Encontre todos os profissionais que atuam na área de desenvolvimento, mostrando nome, idade, faculdade e tempo de experiência"
        },
        "Experiência por Área": {
            "descrição": "Média de experiência por área",
            "query": "Calcule a média de anos de experiência por área de atuação, ordenando do maior para o menor"
        },
        "Profissionais por Idioma": {
            "descrição": "Profissionais por idioma e nível",
            "query": "Liste profissionais que falam inglês em nível avançado ou fluente"
        },
        "Habilidades Comuns": {
            "descrição": "Skills mais frequentes",
            "query": "Mostre as 10 áreas de atuação mais comuns entre os profissionais"
        },
        "Faixa Salarial": {
            "descrição": "Pretensão salarial por área",
            "query": "Calcule a média, mínima e máxima pretensão salarial por área de atuação"
        },
        "Formação Acadêmica": {
            "descrição": "Análise por instituição",
            "query": "Liste as faculdades com mais profissionais formados, incluindo a cidade e estado"
        }
    }

    col1, col2 = st.columns(2)
    exemplo_selecionado = None

    with col1:
        for titulo, info in list(exemplos.items())[:3]:
            if st.button(titulo, help=info['descrição']):
                exemplo_selecionado = info['query']

    with col2:
        for titulo, info in list(exemplos.items())[3:]:
            if st.button(titulo, help=info['descrição']):
                exemplo_selecionado = info['query']

    # Campo de consulta
    query_placeholder = """
    Exemplos do que você pode perguntar:
    - Quais profissionais têm mais de 5 anos de experiência em desenvolvimento?
    - Qual a média salarial pretendida por área de atuação?
    - Quais faculdades formaram mais profissionais?
    """

    prompt = st.text_area(
        "Descreva sua consulta:",
        value=exemplo_selecionado if exemplo_selecionado else st.session_state.get('query_prompt', ''),
        height=100,
        help=query_placeholder
    )

    if st.button("Consultar", type="primary"):
        try:
            with st.spinner("Gerando consulta..."):
                gpt_service = GPTService()
                data_service = DataService()

                # Gerar e mostrar query
                query = gpt_service.gerar_query_sql(prompt, SQL_SCHEMA)

                if query:
                    # Mostrar a query gerada
                    with st.expander("Ver SQL Gerado"):
                        st.code(query, language="sql")

                    # Executar query
                    try:
                        with st.spinner("Executando consulta..."):
                            resultados = data_service.executar_query(query)

                        if resultados:
                            # Converter para DataFrame
                            df = pd.DataFrame(resultados)

                            # Mostrar resultados em tabela
                            st.subheader("Resultados")
                            st.dataframe(df)

                            # Estatísticas básicas se houver dados numéricos
                            numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
                            if len(numeric_cols) > 0:
                                st.subheader("Estatísticas")
                                st.dataframe(df[numeric_cols].describe())

                            # Visualização
                            if len(df) > 1 and len(numeric_cols) > 0:
                                st.subheader("Visualização")

                                # Tipo de gráfico
                                chart_type = st.selectbox(
                                    "Tipo de gráfico:",
                                    ["Barras", "Linha", "Dispersão"]
                                )

                                # Seleção de colunas
                                if len(numeric_cols) > 0:
                                    cols_to_plot = st.multiselect(
                                        "Escolha as colunas para visualizar:",
                                        numeric_cols,
                                        default=[numeric_cols[0]] if len(numeric_cols) > 0 else []
                                    )

                                    if cols_to_plot:
                                        if chart_type == "Barras":
                                            st.bar_chart(df[cols_to_plot])
                                        elif chart_type == "Linha":
                                            st.line_chart(df[cols_to_plot])
                                        else:  # Dispersão
                                            if len(cols_to_plot) >= 2:
                                                st.scatter_chart(data=df, x=cols_to_plot[0], y=cols_to_plot[1])
                                            else:
                                                st.warning(
                                                    "Selecione pelo menos duas colunas para o gráfico de dispersão")
                        else:
                            st.info("Nenhum resultado encontrado")

                    except Exception as e:
                        st.error(f"Erro ao executar a consulta: {str(e)}")
                else:
                    st.error("Não foi possível gerar uma consulta SQL válida")

        except Exception as e:
            st.error(f"Erro na consulta: {str(e)}")

    # Dicas de uso
    with st.expander("Dicas de Uso"):
        st.markdown("""
        ### Como fazer consultas efetivas:
        1. **Seja específico**: Inclua os detalhes que você quer ver no resultado
        2. **Use os nomes das colunas**: Consulte a estrutura do banco na barra lateral
        3. **Combine informações**: Você pode relacionar dados de diferentes tabelas
        4. **Filtre resultados**: Especifique condições para filtrar os dados

        ### Exemplos de consultas complexas:
        - "Mostre os profissionais com mais de 3 anos de experiência em desenvolvimento que falam inglês fluente"
        - "Liste as áreas de atuação com maior média salarial pretendida, incluindo o número de profissionais"
        - "Encontre as faculdades que formaram mais profissionais em tecnologia nos últimos 5 anos"
        """)