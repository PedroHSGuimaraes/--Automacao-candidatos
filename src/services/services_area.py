from src.database.database_connection import DatabaseConnection
import mysql.connector
from src.config.config_settings import DB_CONFIG


class AreaService:
    @staticmethod
    def _get_or_create_area(nome, tipo):
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        try:
            nome = nome.lower().strip()


            cursor.execute("""
                SELECT id, nome, termos_similares 
                FROM areas 
                WHERE LOWER(nome) = LOWER(%s) AND tipo = %s
            """, (nome, tipo))
            resultado = cursor.fetchone()

            if resultado:
                area_id = resultado['id']

                cursor.execute("""
                    UPDATE areas 
                    SET total_uso = COALESCE(total_uso, 0) + 1,
                        ultima_atualizacao = NOW()
                    WHERE id = %s
                """, (area_id,))
            else:

                cursor.execute("""
                    SELECT id, nome, total_uso
                    FROM areas 
                    WHERE tipo = %s AND (
                        LOWER(nome) LIKE %s
                        OR MATCH(nome, descricao, termos_similares) AGAINST(%s IN BOOLEAN MODE)
                    )
                    ORDER BY total_uso DESC
                    LIMIT 1
                """, (tipo, f"%{nome}%", nome))

                similar = cursor.fetchone()
                if similar:
                    area_id = similar['id']

                    cursor.execute("""
                        UPDATE areas 
                        SET total_uso = COALESCE(total_uso, 0) + 1,
                            ultima_atualizacao = NOW(),
                            termos_similares = CONCAT_WS(',', termos_similares, %s)
                        WHERE id = %s
                    """, (nome, area_id))
                else:
                    # Cria nova área
                    cursor.execute("""
                        INSERT INTO areas 
                        (nome, tipo, descricao, termos_similares, total_uso) 
                        VALUES (%s, %s, %s, %s, 1)
                    """, (
                        nome,
                        tipo,
                        f"Área {tipo} identificada a partir do termo: {nome}",
                        nome
                    ))
                    area_id = cursor.lastrowid

            conn.commit()
            return area_id

        except Exception as e:
            conn.rollback()
            print(f"Erro ao criar/buscar área '{nome}' do tipo '{tipo}': {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    def buscar_areas_similares(self, termo, tipo):
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        try:
            termo_lower = termo.lower()


            query = """
            SELECT 
                id, 
                nome, 
                total_uso,
                termos_similares,
                MATCH(nome, descricao, termos_similares) AGAINST(%s) as relevancia
            FROM areas 
            WHERE tipo = %s 
            AND (
                LOWER(nome) LIKE %s
                OR MATCH(nome, descricao, termos_similares) AGAINST(%s IN BOOLEAN MODE)
            )
            ORDER BY relevancia DESC, total_uso DESC
            LIMIT 5
            """

            cursor.execute(query, (
                termo_lower,
                tipo,
                f"%{termo_lower}%",
                termo_lower
            ))

            return cursor.fetchall()

        except Exception as e:
            print(f"Erro ao buscar áreas similares para '{termo}' do tipo '{tipo}': {e}")
            return []
        finally:
            cursor.close()
            conn.close()

    def associar_areas_candidato(self, candidato_id, areas_interesse, areas_atuacao):
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        try:

            cursor.execute(
                "DELETE FROM candidato_areas WHERE candidato_id = %s",
                (candidato_id,)
            )

            # Processa áreas de interesse
            for area in areas_interesse:
                if area and len(str(area).strip()) > 0:
                    try:
                        area_id = self._get_or_create_area(area, 'interesse')
                        cursor.execute("""
                            INSERT INTO candidato_areas 
                            (candidato_id, area_id, tipo) 
                            VALUES (%s, %s, 'interesse')
                        """, (candidato_id, area_id))
                    except Exception as e:
                        print(f"Erro ao associar área de interesse '{area}': {e}")

            # Processa áreas de atuação
            for area in areas_atuacao:
                if area and len(str(area).strip()) > 0:
                    try:
                        area_id = self._get_or_create_area(area, 'atuacao')
                        cursor.execute("""
                            INSERT INTO candidato_areas 
                            (candidato_id, area_id, tipo) 
                            VALUES (%s, %s, 'atuacao')
                        """, (candidato_id, area_id))
                    except Exception as e:
                        print(f"Erro ao associar área de atuação '{area}': {e}")

            conn.commit()

        except Exception as e:
            conn.rollback()
            print(f"Erro ao associar áreas para candidato {candidato_id}: {e}")
            raise
        finally:
            cursor.close()
            conn.close()