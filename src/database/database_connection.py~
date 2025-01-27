# src/database/connection.py
import mysql.connector
from src.config.config_settings import DB_CONFIG, SQL_SCHEMA

class DatabaseConnection:
    @staticmethod
    def get_connection():
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor(dictionary=True)
            cursor.execute(SQL_SCHEMA)
            conn.commit()
            return conn, cursor
        except Exception as e:
            raise ConnectionError(f"Erro na conexão com banco: {e}")

    @staticmethod
    def close_connection(conn, cursor):
        if cursor:
            cursor.close()
        if conn:
            conn.close()