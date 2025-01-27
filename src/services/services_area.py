# src/services/services_area.py
from src.database.database_connection import DatabaseConnection
import mysql.connector
from src.config.config_settings import DB_CONFIG


class AreaService:
    @staticmethod
    def _get_or_create_area(nome, tipo):
        """Busca uma área existente ou cria uma nova"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        try:
            # Primeiro tenta buscar a área
            cursor.execute(
                "SELECT id FROM areas WHERE LOWER(nome) = LOWER(%s) AND tipo = %s",
                (nome.lower(), tipo)
            )
            resultado = cursor.fetchone()

            if resultado:
                # Se encontrou, atualiza o contador
                cursor.execute(
                    "UPDATE areas SET total_uso = total_uso + 1 WHERE id = %s",
                    (resultado['id'],)
                )
                area_id = resultado['id']
            else:
                # Se não encontrou, cria nova
                cursor.execute(
                    "INSERT INTO areas (nome, tipo) VALUES (%s, %s)",
                    (nome.lower(), tipo)
                )
                area_id = cursor.lastrowid

            conn.commit()
            return area_id
        finally:
            cursor.close()
            conn.close()

    def associar_areas_candidato(self, candidato_id, areas_interesse, areas_atuacao):
        """Associa áreas ao candidato"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        try:
            # Limpa associações anteriores
            cursor.execute(
                "DELETE FROM candidato_areas WHERE candidato_id = %s",
                (candidato_id,)
            )

            # Processa áreas de interesse
            for area in areas_interesse:
                if area and len(area.strip()) > 0:  # Ignora strings vazias
                    area_id = self._get_or_create_area(area, 'interesse')
                    cursor.execute(
                        """INSERT INTO candidato_areas 
                           (candidato_id, area_id, tipo) VALUES (%s, %s, 'interesse')""",
                        (candidato_id, area_id)
                    )

            # Processa áreas de atuação
            for area in areas_atuacao:
                if area and len(area.strip()) > 0:  # Ignora strings vazias
                    area_id = self._get_or_create_area(area, 'atuacao')
                    cursor.execute(
                        """INSERT INTO candidato_areas 
                           (candidato_id, area_id, tipo) VALUES (%s, %s, 'atuacao')""",
                        (candidato_id, area_id)
                    )

            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Erro ao associar áreas: {e}")
            # Não propaga o erro para não interromper o processo
        finally:
            cursor.close()
            conn.close()

    def buscar_areas_similares(self, termo, tipo):
        """Busca áreas similares usando LIKE"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        try:
            query = """
            SELECT id, nome, total_uso 
            FROM areas 
            WHERE tipo = %s 
            AND LOWER(nome) LIKE %s 
            ORDER BY total_uso DESC 
            LIMIT 5
            """
            cursor.execute(query, (tipo, f"%{termo.lower()}%"))
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()