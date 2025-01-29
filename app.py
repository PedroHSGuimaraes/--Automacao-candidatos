import streamlit as st
from src.ui.ui_components import render_query, render_viewer, render_upload
from src.config.config_settings import UI_CONFIG

st.set_page_config(
    page_title="Analisador de Currículos",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)


def main():
    # Título principal
    st.title("📄 Analisador de Currículos")

    # Menu lateral
    with st.sidebar:
        st.header("Menu")
        menu = st.radio(
            "Escolha uma opção",
            ["Upload de CVs", "Visualizar Dados", "Consultas Personalizadas"]
        )

        # Informações adicionais
        st.sidebar.markdown("---")
        st.sidebar.info("""
        ### Sobre
        Este sistema utiliza IA para analisar currículos e extrair informações relevantes.

        **Recursos:**
        - Upload de PDFs
        - Análise automática
        - Visualização de dados
        - Consultas personalizadas
        """)



    # Renderiza o componente selecionado
    if menu == "Upload de CVs":
        render_upload()
    elif menu == "Visualizar Dados":
        render_viewer()
    elif menu == "Consultas Personalizadas":
        render_query()

    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center'>
            <p>Desenvolvido com ❤️ usando Streamlit e OpenAI</p>
        </div>
        """,
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()