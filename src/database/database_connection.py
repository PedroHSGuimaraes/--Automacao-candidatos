# src/database/database_connection.py
import mysql.connector
from src.config.config_settings import DB_CONFIG, SQL_SCHEMA


class DatabaseConnection:
    @staticmethod
    def get_connection():
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor(dictionary=True)

            # Executa as queries do schema separadamente
            for query in SQL_SCHEMA.split(';'):
                if query.strip():  # Ignora strings vazias
                    cursor.execute(query.strip())
            conn.commit()

            return conn, cursor
        except Exception as e:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()
            raise ConnectionError(f"Erro na conexão com banco: {e}")

    @staticmethod
    def close_connection(conn, cursor):
        try:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
        except Exception as e:
            print(f"Erro ao fechar conexão: {e}")

    @staticmethod
    def execute_query(query, params=None):
        conn = None
        cursor = None
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor(dictionary=True)
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            result = cursor.fetchall()
            conn.commit()
            return result
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()