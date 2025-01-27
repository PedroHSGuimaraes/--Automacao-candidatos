# src/services/data_service.py
import json
from datetime import datetime
from src.database.database_connection import DatabaseConnection


class DataService:
    @staticmethod
    def salvar_candidato(dados, texto_pdf):
        conn, cursor = DatabaseConnection.get_connection()
        try:
            query = """
            INSERT INTO candidatos (
                nome, email, genero, idade, instituto_formacao, curso, periodo,
                tempo_experiencia, area_atuacao, ultima_experiencia, todas_experiencias,
                habilidades, linkedin, github, telefone, data_criacao, pdf_conteudo,
                observacoes_ia, campos_dinamicos
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            valores = (
                dados['dados_basicos']['nome'],
                dados['dados_basicos']['email'],
                dados['dados_basicos']['genero'],
                dados['dados_basicos']['idade'],
                dados['formacao']['instituto_formacao'],
                dados['formacao']['curso'],
                dados['formacao']['periodo'],
                dados['experiencia']['tempo_experiencia'],
                dados['experiencia']['area_atuacao'],
                dados['experiencia']['ultima_experiencia'],
                json.dumps(dados['experiencia']['todas_experiencias']),
                json.dumps(dados['habilidades']),
                dados['contato']['linkedin'],
                dados['contato']['github'],
                dados['contato']['telefone'],
                datetime.now(),
                texto_pdf,
                json.dumps(dados['observacoes_ia']),
                json.dumps(dados['campos_dinamicos'])
            )
            cursor.execute(query, valores)
            conn.commit()
            return True
        except Exception as e:
            raise Exception(f"Erro ao salvar candidato: {e}")
        finally:
            DatabaseConnection.close_connection(conn, cursor)

    @staticmethod
    def buscar_candidatos():
        conn, cursor = DatabaseConnection.get_connection()
        try:
            cursor.execute("SELECT * FROM candidatos")
            return cursor.fetchall()
        finally:
            DatabaseConnection.close_connection(conn, cursor)

    @staticmethod
    def executar_query(query):
        conn, cursor = DatabaseConnection.get_connection()
        try:
            cursor.execute(query)
            return cursor.fetchall()
        finally:
            DatabaseConnection.close_connection(conn, cursor)