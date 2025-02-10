# src/ui/ui_components.py

import streamlit as st
import pandas as pd
from src.config.config_settings import SQL_SCHEMA
from src.services.services_gpt import GPTService
from src.services.services_pdf import PDFService
from src.services.services_data import DataService
from src.ui.styles import QUERY_STYLES, UPLOAD_STYLES, VIEWER_STYLES


def render_upload():
    st.markdown(UPLOAD_STYLES, unsafe_allow_html=True)
    st.header("Upload de Currículos")

    with st.container():
        arquivos = st.file_uploader(
            "Selecione os PDFs dos currículos",
            type="pdf",
            accept_multiple_files=True,
            help="Você pode selecionar múltiplos arquivos PDF ou um único PDF com vários currículos"
        )

        if arquivos:
            gpt_service = GPTService()
            pdf_service = PDFService()
            data_service = DataService()

            progress_bar = st.progress(0)
            status_text = st.empty()

            total_processado = 0
            total_curriculos = 0


            for arquivo in arquivos:
                try:
                    curriculos = pdf_service.extrair_curriculos_multiplos(arquivo)
                    total_curriculos += len(curriculos)
                except Exception as e:
                    st.error(f"Erro ao analisar {arquivo.name}: {e}")
                    continue


            for arquivo in arquivos:
                try:

                    curriculos = pdf_service.extrair_curriculos_multiplos(arquivo)


                    st.info(f"Encontrados {len(curriculos)} currículos em {arquivo.name}")


                    if curriculos:
                        st.write("Candidatos identificados neste arquivo:")
                        dados_candidatos = []
                        for info, _ in curriculos:
                            dados_candidatos.append({
                                "Nome": info.get('nome', 'Não identificado'),
                                "Email": info.get('email', 'Não informado'),
                                "Telefone": info.get('telefone', 'Não informado')
                            })
                        st.table(dados_candidatos)


                    for idx, (info, texto_cv) in enumerate(curriculos, 1):
                        total_processado += 1
                        progress = total_processado / total_curriculos
                        progress_bar.progress(progress)

                        nome_candidato = info.get('nome', f'Candidato {idx}')
                        status_text.text(
                            f"Processando currículo de {nome_candidato} ({idx}/{len(curriculos)}) do arquivo {arquivo.name}")

                        try:
                            with st.spinner(f'Analisando currículo de {nome_candidato}...'):
                                dados = gpt_service.analisar_curriculo(texto_cv)


                                if not dados['profissional']['nome'] and info.get('nome'):
                                    dados['profissional']['nome'] = info['nome']
                                if not dados['profissional']['email'] and info.get('email'):
                                    dados['profissional']['email'] = info['email']
                                if not dados['profissional']['telefone'] and info.get('telefone'):
                                    dados['profissional']['telefone'] = info['telefone']

                                data_service.salvar_profissional(dados, texto_cv)
                                st.success(f"✅ Currículo de {nome_candidato} processado com sucesso")
                        except Exception as e:
                            st.error(f"❌ Erro ao processar currículo de {nome_candidato}: {e}")

                except Exception as e:
                    st.error(f"❌ Erro ao processar arquivo {arquivo.name}: {e}")

            progress_bar.empty()
            status_text.empty()


            st.markdown("### Resumo do Processamento")
            st.markdown(f"""
            - Total de arquivos processados: {len(arquivos)}
            - Total de currículos encontrados: {total_curriculos}
            - Total de currículos processados com sucesso: {total_processado}
            """)

def render_viewer():
    st.markdown(VIEWER_STYLES, unsafe_allow_html=True)
    st.header("Visualização dos Dados")

    try:
        data_service = DataService()


        tabela_selecionada = st.selectbox(
            "Selecione a tabela para visualizar:",
            [
                "Profissionais",
                "Gêneros",
                "Faculdades",
                "Idiomas",
                "Áreas de Interesse",
                "Áreas de Atuação",
                "Profissionais-Idiomas",
                "Profissionais-Áreas de Interesse",
                "Profissionais-Áreas de Atuação"
            ]
        )


        if tabela_selecionada == "Profissionais":
            query = """
                SELECT p.*, 
                    p.cargo_atual,
                    g.nome as genero,
                    f.nome as faculdade,
                    i.nome as idioma_principal,
                    p.habilidades
                FROM profissionais p
                LEFT JOIN generos g ON p.genero_id = g.id
                LEFT JOIN faculdades f ON p.faculdade_id = f.id
                LEFT JOIN idiomas i ON p.idioma_principal_id = i.id
            """
        elif tabela_selecionada == "Gêneros":
            query = "SELECT * FROM generos"
        elif tabela_selecionada == "Faculdades":
            query = "SELECT * FROM faculdades"
        elif tabela_selecionada == "Idiomas":
            query = "SELECT * FROM idiomas"
        elif tabela_selecionada == "Áreas de Interesse":
            query = "SELECT * FROM areas_interesse"
        elif tabela_selecionada == "Áreas de Atuação":
            query = "SELECT * FROM areas_atuacao"
        elif tabela_selecionada == "Profissionais-Idiomas":
            query = """
                SELECT p.nome as profissional, 
                       i.nome as idioma,
                       pi.nivel,
                       pi.certificacao,
                       pi.data_certificacao
                FROM profissionais_idiomas pi
                JOIN profissionais p ON pi.profissional_id = p.id
                JOIN idiomas i ON pi.idioma_id = i.id
            """
        elif tabela_selecionada == "Profissionais-Áreas de Interesse":
            query = """
                SELECT p.nome as profissional,
                       ai.nome as area_interesse,
                       pai.nivel_interesse
                FROM profissionais_areas_interesse pai
                JOIN profissionais p ON pai.profissional_id = p.id
                JOIN areas_interesse ai ON pai.area_interesse_id = ai.id
            """
        else:
            query = """
                SELECT p.nome as profissional,
                       aa.nome as area_atuacao,
                       paa.anos_experiencia,
                       paa.ultimo_cargo,
                       paa.ultima_empresa,
                       paa.data_inicio,
                       paa.data_fim,
                       paa.descricao_atividades
                FROM profissionais_areas_atuacao paa
                JOIN profissionais p ON paa.profissional_id = p.id
                JOIN areas_atuacao aa ON paa.area_atuacao_id = aa.id
            """


        dados = data_service.executar_query(query)

        if dados:
            df = pd.DataFrame(dados)


            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total de Registros", len(df))
            with col2:
                if 'nome' in df.columns:
                    st.metric("Registros Únicos", df['nome'].nunique())


            st.subheader(f"Dados da tabela: {tabela_selecionada}")
            st.dataframe(df)


            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Baixar dados como CSV",
                csv,
                f"{tabela_selecionada.lower().replace(' ', '_')}.csv",
                "text/csv",
                key='download-csv'
            )

            if len(df) > 1:
                st.subheader("Visualizações")

                if tabela_selecionada == "Profissionais":
                    col1, col2 = st.columns(2)
                    with col1:
                        if 'cargo_atual' in df.columns:
                            st.write("Distribuição por Cargo")
                            cargo_counts = df['cargo_atual'].value_counts()
                            st.bar_chart(cargo_counts)
                    with col2:
                        if 'idade' in df.columns:
                            st.write("Distribuição por Idade")
                            idade_bins = pd.cut(df['idade'].dropna(),
                                                bins=[0, 20, 25, 30, 35, 40, 45, 50, 100],
                                                labels=['0-20', '21-25', '26-30', '31-35',
                                                        '36-40', '41-45', '46-50', '50+'])
                            idade_counts = idade_bins.value_counts()
                            st.bar_chart(idade_counts)

                elif tabela_selecionada == "Profissionais-Idiomas":
                    if 'idioma' in df.columns:
                        st.write("Distribuição por Idioma")
                        idioma_counts = df['idioma'].value_counts()
                        st.bar_chart(idioma_counts)

                        st.write("Distribuição por Nível")
                        nivel_counts = df['nivel'].value_counts()
                        st.bar_chart(nivel_counts)

                elif tabela_selecionada == "Profissionais-Áreas de Atuação":
                    if 'area_atuacao' in df.columns:
                        st.write("Distribuição por Área de Atuação")
                        area_counts = df['area_atuacao'].value_counts()
                        st.bar_chart(area_counts)

                        if 'anos_experiencia' in df.columns:
                            st.write("Distribuição por Anos de Experiência")
                            exp_bins = pd.cut(df['anos_experiencia'].dropna(),
                                              bins=[0, 2, 5, 8, 100],
                                              labels=['0-2 anos', '2-5 anos',
                                                      '5-8 anos', '8+ anos'])
                            exp_counts = exp_bins.value_counts()
                            st.bar_chart(exp_counts)
        else:
            st.info(f"Nenhum dado encontrado na tabela {tabela_selecionada}")

    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")


def render_query():
    st.markdown(QUERY_STYLES, unsafe_allow_html=True)
    st.title("Sistema de Consulta de Currículos")

    tab1, tab2 = st.tabs(["📝 Consulta", "📊 Estrutura do Banco"])

    with tab1:
        st.header("Consultas Personalizadas")


        st.subheader("Exemplos de Consultas")
        col1, col2 = st.columns(2)

        with col1:
            with st.expander("🎯 Consultas por Perfil", expanded=True):
                exemplos_perfil = {
                    "Profissionais por Área": "Encontre todos os profissionais que atuam na área de desenvolvimento",
                    "Profissionais por Idioma": "Liste profissionais que falam inglês fluente",
                    "Experiência Específica": "Busque profissionais com mais de 5 anos de experiência em Python"
                }
                for titulo, query in exemplos_perfil.items():
                    if st.button(titulo, key=f"btn_{titulo}"):
                        st.session_state['query_prompt'] = query

        with col2:
            with st.expander("📊 Consultas Analíticas", expanded=True):
                exemplos_analiticos = {
                    "Média Salarial": "Calcule a média salarial pretendida por área de atuação",
                    "Distribuição por Idade": "Mostre a distribuição de idade dos profissionais por área",
                    "Top Habilidades": "Liste as 10 habilidades mais comuns entre os profissionais"
                }
                for titulo, query in exemplos_analiticos.items():
                    if st.button(titulo, key=f"btn_analytic_{titulo}"):
                        st.session_state['query_prompt'] = query


        st.markdown("---")
        prompt = st.text_area(
            "Digite sua consulta:",
            value=st.session_state.get('query_prompt', ''),
            height=100,
            placeholder="Ex: Busque profissionais formados em Engenharia que falam inglês fluente..."
        )


        if st.button("🔍 Consultar", type="primary"):
            try:
                with st.spinner("Gerando consulta..."):
                    gpt_service = GPTService()
                    data_service = DataService()

                    query = gpt_service.gerar_query_sql(prompt, SQL_SCHEMA)

                    if query:
                        with st.expander("🔍 SQL Gerado"):
                            st.code(query, language="sql")

                        try:
                            with st.spinner("Executando consulta..."):
                                resultados = data_service.executar_query(query)

                            if resultados:

                                df = pd.DataFrame(resultados)


                                col1, col2 = st.columns([2, 1])

                                with col1:
                                    st.subheader("Resultados")
                                    st.dataframe(df)

                                with col2:
                                    st.subheader("Resumo")
                                    st.metric("Total de Registros", len(df))

                                    num_cols = df.select_dtypes(include=['int64', 'float64']).columns
                                    if len(num_cols) > 0:
                                        st.markdown("**Análise Numérica**")
                                        st.dataframe(df[num_cols].describe())

                                if len(df) > 1:
                                    st.subheader("Visualização")

                                    chart_type = st.selectbox(
                                        "Tipo de Gráfico:",
                                        ["Barras", "Linha", "Dispersão"]
                                    )

                                    if len(num_cols) > 0:
                                        cols_to_plot = st.multiselect(
                                            "Colunas para visualizar:",
                                            num_cols
                                        )

                                        if cols_to_plot:
                                            if chart_type == "Barras":
                                                st.bar_chart(df[cols_to_plot])
                                            elif chart_type == "Linha":
                                                st.line_chart(df[cols_to_plot])
                                            else:
                                                if len(cols_to_plot) >= 2:
                                                    st.scatter_chart(
                                                        data=df,
                                                        x=cols_to_plot[0],
                                                        y=cols_to_plot[1]
                                                    )
                                                else:
                                                    st.warning(
                                                        "Selecione duas colunas para o gráfico de dispersão"
                                                    )
                            else:
                                st.info("Nenhum resultado encontrado")

                        except Exception as e:
                            st.error(f"Erro ao executar a consulta: {str(e)}")
                    else:
                        st.error("Não foi possível gerar uma consulta SQL válida")

            except Exception as e:
                st.error(f"Erro na consulta: {str(e)}")

    with tab2:
        st.header("Estrutura do Banco de Dados")


        with st.expander("🎯 Tabelas Principais", expanded=True):
            tabelas_principais = {
                "profissionais": {
                    "descrição": "Informações principais dos profissionais",
                    "colunas": [
                        "id", "nome", "email", "telefone", "endereco", "portfolio_url",
                        "linkedin_url", "github_url", "cargo_atual", "faculdade_id",
                        "genero_id", "idioma_principal_id", "nivel_idioma_principal",
                        "idade", "pretensao_salarial", "disponibilidade", "tipo_contrato"
                    ]
                },
                "generos": {
                    "descrição": "Tipos de gênero",
                    "colunas": ["id", "nome", "descricao"]
                },
                "faculdades": {
                    "descrição": "Instituições de ensino",
                    "colunas": ["id", "nome", "cidade", "estado", "pais", "tipo", "ranking"]
                },
                "idiomas": {
                    "descrição": "Cadastro de idiomas",
                    "colunas": ["id", "nome", "codigo"]
                }
            }

            for nome, info in tabelas_principais.items():
                st.markdown(f"**{nome}**")
                st.markdown(f"_{info['descrição']}_")
                cols = [f"`{col}`" for col in info['colunas']]
                st.markdown(", ".join(cols))
                st.markdown("---")

        with st.expander("🎯 Tabelas de Interesse e Atuação", expanded=True):
            tabelas_areas = {
                "areas_interesse": {
                    "descrição": "Áreas de interesse profissional",
                    "colunas": ["id", "nome", "descricao", "total_uso", "termos_similares"]
                },
                "areas_atuacao": {
                    "descrição": "Áreas de atuação profissional",
                    "colunas": ["id", "nome", "descricao", "total_uso", "termos_similares"]
                }
            }

            for nome, info in tabelas_areas.items():
                st.markdown(f"**{nome}**")
                st.markdown(f"_{info['descrição']}_")
                cols = [f"`{col}`" for col in info['colunas']]
                st.markdown(", ".join(cols))
                st.markdown("---")

        with st.expander("🔗 Tabelas de Relacionamento", expanded=True):
            relacionamentos = {
                "profissionais_idiomas": {
                    "descrição": "Relaciona profissionais e seus idiomas",
                    "colunas": [
                        "profissional_id",
                        "idioma_id",
                        "nivel",
                        "certificacao",
                        "data_certificacao"
                    ]
                },
                "profissionais_areas_interesse": {
                    "descrição": "Relaciona profissionais e suas áreas de interesse",
                    "colunas": [
                        "profissional_id",
                        "area_interesse_id",
                        "nivel_interesse"
                    ]
                },
                "profissionais_areas_atuacao": {
                    "descrição": "Relaciona profissionais e suas áreas de atuação",
                    "colunas": [
                        "profissional_id",
                        "area_atuacao_id",
                        "anos_experiencia",
                        "ultimo_cargo",
                        "ultima_empresa",
                        "data_inicio",
                        "data_fim",
                        "descricao_atividades"
                    ]
                }
            }

            for nome, info in relacionamentos.items():
                st.markdown(f"**{nome}**")
                st.markdown(f"_{info['descrição']}_")
                cols = [f"`{col}`" for col in info['colunas']]
                st.markdown(", ".join(cols))
                st.markdown("---")

        # Guia de Consultas
        with st.expander("💡 Guia de Consultas", expanded=True):
            st.markdown("""
            ### Como fazer consultas efetivas:
            1. **Seja específico**: Inclua os detalhes que deseja ver no resultado
            2. **Use os nomes das tabelas**: Consulte a estrutura acima
            3. **Combine informações**: Relacione dados de diferentes tabelas
            4. **Filtre resultados**: Especifique condições para filtrar os dados

            ### Exemplos de consultas complexas:
            - "Encontre profissionais com mais de 3 anos de experiência em desenvolvimento que falam inglês fluente"
            - "Liste as áreas de atuação com maior média salarial pretendida"
            - "Mostre as faculdades que formaram mais profissionais em tecnologia"
            - "Busque profissionais com experiência em Python e certificação em AWS"

            ### Dicas para filtros:
            - Use termos específicos como "desenvolvimento", "python", "aws"
            - Especifique anos de experiência quando relevante
            - Combine múltiplos critérios para resultados mais precisos
            - Considere incluir níveis de proficiência em idiomas
            """)


def render_dashboard():
    st.markdown(VIEWER_STYLES, unsafe_allow_html=True)
    st.header("Dashboard de Análise")

    try:
        data_service = DataService()
        dados = data_service.buscar_

        with st.expander("📝 Exemplos de SQL", expanded=True):
            st.markdown("""
            ### Consultas SQL de Exemplo:

            1. **Busca básica de profissionais:**
            ```sql
            SELECT p.nome, p.cargo_atual, g.nome as genero
            FROM profissionais p
            LEFT JOIN generos g ON p.genero_id = g.id
            ```

            2. **Profissionais com idiomas:**
            ```sql
            SELECT p.nome, i.nome as idioma, pi.nivel
            FROM profissionais p
            LEFT JOIN profissionais_idiomas pi ON p.id = pi.profissional_id
            LEFT JOIN idiomas i ON pi.idioma_id = i.id
            WHERE LOWER(i.nome) = 'inglês' AND pi.nivel IN ('avançado', 'fluente')
            ```

            3. **Experiência em área específica:**
            ```sql
            SELECT p.nome, aa.nome as area, paa.anos_experiencia
            FROM profissionais p
            LEFT JOIN profissionais_areas_atuacao paa ON p.id = paa.profissional_id
            LEFT JOIN areas_atuacao aa ON paa.area_atuacao_id = aa.id
            WHERE LOWER(aa.nome) LIKE '%desenvolvimento%'
            AND paa.anos_experiencia >= 3
            ```
            """)

        with st.expander("📊 Tabelas Principais", expanded=True):
            st.write(dados)

    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")