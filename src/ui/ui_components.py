# src/ui/ui_components.py
import streamlit as st
import pandas as pd
from src.config.config_settings import SQL_SCHEMA
from src.services.services_gpt import GPTService
from src.services.services_pdf import PDFService
from src.services.services_data import DataService


# src/ui/ui_components.py
def render_query():
    st.header("Consultas Personalizadas")

    tipo_consulta = st.selectbox(
        "Tipo de Consulta",
        [
            "Geral",
            "Busca por Habilidades",
            "Filtro por Experiência",
            "Análise de Áreas",
            "Busca por Formação",
            "Ranking de Candidatos"
        ]
    )

    # Dicas e exemplos baseados no tipo selecionado
    exemplos = {
        "Geral": [
            "Mostre todos os candidatos que têm experiência com Python",
            "Liste os candidatos ordenados por tempo de experiência",
            "Quais candidatos têm GitHub cadastrado?"
        ],
        "Busca por Habilidades": [
            "Encontre candidatos que conhecem React e Node.js",
            "Quais candidatos têm experiência com banco de dados?",
            "Liste as habilidades mais comuns entre os candidatos"
        ],
        "Filtro por Experiência": [
            "Candidatos com mais de 2 anos de experiência",
            "Quem tem experiência em desenvolvimento fullstack?",
            "Mostre a média de experiência por área de atuação"
        ],
        "Análise de Áreas": [
            "Quais são as áreas de interesse mais comuns?",
            "Candidatos que têm interesse em IA",
            "Compare áreas de interesse com áreas de atuação"
        ],
        "Busca por Formação": [
            "Candidatos formados em Engenharia",
            "Liste as instituições de ensino",
            "Quem está cursando ciência da computação?"
        ],
        "Ranking de Candidatos": [
            "Top 5 candidatos com mais habilidades técnicas",
            "Ranking por tempo de experiência",
            "Candidatos mais qualificados em desenvolvimento"
        ]
    }

    # Mostra exemplos para o tipo selecionado
    st.info(f"💡 Exemplos de consultas para {tipo_consulta}:")
    for exemplo in exemplos[tipo_consulta]:
        st.markdown(f"• {exemplo}")

    # Campo de consulta e botão
    prompt = st.text_area("Digite sua consulta:", height=100)
    if st.button("Consultar"):
        try:
            with st.spinner('Gerando e executando consulta...'):
                gpt_service = GPTService()
                data_service = DataService()

                # Adiciona o tipo de consulta ao contexto
                contexto = f"""
                Tipo de consulta: {tipo_consulta}
                Consulta do usuário: {prompt}

                Utilize as seguintes tabelas relacionadas:
                1. candidatos (dados básicos, formação e experiência)
                2. areas (áreas de interesse e atuação)
                3. candidato_areas (relacionamento entre candidatos e áreas)

                Considere que:
                - Campos JSON devem ser tratados com JSON_CONTAINS ou JSON_EXTRACT
                - Use LOWER() para comparações case-insensitive
                - Junte as tabelas quando necessário para informações de áreas
                """

                schema = "Considere a tabela a seguir: " + SQL_SCHEMA

                query = gpt_service.gerar_query_sql(contexto, schema)
                if query:
                    st.code(query, language="sql")
                    try:
                        resultados = data_service.executar_query(query)

                        if resultados:
                            df = pd.DataFrame(resultados)
                            st.dataframe(df)

                            # Adiciona botão de download
                            csv = df.to_csv(index=False)
                            st.download_button(
                                "📥 Baixar Resultados (CSV)",
                                csv,
                                "resultados_consulta.csv",
                                "text/csv",
                                key='download-csv'
                            )
                        else:
                            st.info("Nenhum resultado encontrado")
                    except Exception as e:
                        st.error(f"Erro ao executar a query: {str(e)}")
                else:
                    st.error("Não foi possível gerar uma query SQL válida.")
        except Exception as e:
            st.error(f"Erro na consulta: {str(e)}")
# src/ui/ui_components.py



def safe_json_loads(value, default=None):
    if not value:
        return default or []
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except:
        return default or []


def safe_join(value, separator=", "):
    if not value:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return separator.join(str(v) for v in value if v)
    return str(value)


def render_viewer():
    st.header("Visualização de Dados")

    try:
        data_service = DataService()

        # Busca dados de todas as tabelas
        with st.spinner('Carregando dados...'):
            # Tabela candidatos
            query_candidatos = "SELECT * FROM candidatos"
            dados_candidatos = data_service.executar_query(query_candidatos)

            # Tabela areas
            query_areas = "SELECT * FROM areas ORDER BY total_uso DESC"
            dados_areas = data_service.executar_query(query_areas)

            # Tabela candidato_areas com JOIN para nomes
            query_candidato_areas = """
            SELECT ca.id, c.nome as candidato_nome, a.nome as area_nome, 
                   ca.tipo, a.total_uso
            FROM candidato_areas ca
            JOIN candidatos c ON ca.candidato_id = c.id
            JOIN areas a ON ca.area_id = a.id
            ORDER BY c.nome, ca.tipo
            """
            dados_candidato_areas = data_service.executar_query(query_candidato_areas)

            # Define as tabs
            tab1, tab2, tab3, tab4, tab5 = st.tabs([
                "📊 Dashboard",
                "👥 Candidatos",
                "🎯 Áreas",
                "🔗 Relacionamentos",
                "📝 Dados Completos"
            ])

            with tab1:
                st.subheader("Dashboard")

                # Métricas gerais
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total de Candidatos", len(dados_candidatos))
                with col2:
                    st.metric("Total de Áreas", len(dados_areas))
                with col3:
                    st.metric("Total de Relacionamentos", len(dados_candidato_areas))

                # Top áreas
                st.subheader("Top 10 Áreas mais utilizadas")
                df_top_areas = pd.DataFrame(dados_areas[:10])
                if not df_top_areas.empty:
                    df_top_areas = df_top_areas[['nome', 'tipo', 'total_uso']]
                    st.dataframe(df_top_areas, use_container_width=True)

            with tab2:
                st.subheader("Tabela de Candidatos")
                if dados_candidatos:
                    df_candidatos = pd.DataFrame(dados_candidatos)
                    # Remove campos muito grandes
                    if 'pdf_conteudo' in df_candidatos.columns:
                        df_candidatos = df_candidatos.drop('pdf_conteudo', axis=1)
                    st.dataframe(df_candidatos, use_container_width=True)
                else:
                    st.info("Nenhum candidato encontrado")

            with tab3:
                st.subheader("Tabela de Áreas")
                if dados_areas:
                    df_areas = pd.DataFrame(dados_areas)
                    st.dataframe(df_areas, use_container_width=True)
                else:
                    st.info("Nenhuma área encontrada")

            with tab4:
                st.subheader("Relacionamentos Candidato-Áreas")
                if dados_candidato_areas:
                    df_rel = pd.DataFrame(dados_candidato_areas)
                    st.dataframe(df_rel, use_container_width=True)
                else:
                    st.info("Nenhum relacionamento encontrado")

            with tab5:
                st.subheader("Dados Completos dos Candidatos")
                if dados_candidatos:
                    dados_limpos = []
                    for d in dados_candidatos:
                        d_clean = d.copy()
                        if 'pdf_conteudo' in d_clean:
                            del d_clean['pdf_conteudo']
                        for campo in ['habilidades', 'todas_experiencias', 'observacoes_ia', 'campos_dinamicos']:
                            if campo in d_clean:
                                d_clean[campo] = safe_join(safe_json_loads(d_clean.get(campo)))
                        dados_limpos.append(d_clean)

                    df_completo = pd.DataFrame(dados_limpos)
                    st.dataframe(df_completo, use_container_width=True)
                else:
                    st.info("Nenhum dado encontrado")

    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")
        st.exception(e)



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
                    if data_service.salvar_candidato(dados, texto_pdf):
                        st.success(f"✅ {arquivo.name} processado com sucesso")
                    else:
                        st.error(f"❌ Erro ao salvar {arquivo.name}")
                except Exception as e:
                    st.error(f"❌ Erro ao processar {arquivo.name}: {str(e)}")