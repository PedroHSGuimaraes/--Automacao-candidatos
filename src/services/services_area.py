from src.database.database_connection import DatabaseConnection
import mysql.connector
from src.config.config_settings import DB_CONFIG
from src.utils.classes_profissao import profissoes_classes


class AreaService:
    @staticmethod
    def _get_or_create_area(nome, tipo):
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        try:
            # Padronizar o nome baseado nas profissoes_classes
            nome = nome.lower().strip()
            nome_padrao = None

            # Procura correspondência exata
            if nome in profissoes_classes:
                nome_padrao = nome
            else:
                # Procura nas listas de similares
                for area_padrao, similares in profissoes_classes.items():
                    if nome in similares:
                        nome_padrao = area_padrao
                        break

            # Se não encontrou, usa o nome original
            if nome_padrao is None:
                nome_padrao = nome

            # Busca a área no banco
            cursor.execute(
                "SELECT id FROM areas WHERE LOWER(nome) = LOWER(%s) AND tipo = %s",
                (nome_padrao, tipo)
            )
            resultado = cursor.fetchone()

            if resultado:
                # Atualiza o contador de uso
                cursor.execute(
                    "UPDATE areas SET total_uso = total_uso + 1 WHERE id = %s",
                    (resultado['id'],)
                )
                area_id = resultado['id']
            else:
                # Cria nova área com o nome padronizado
                cursor.execute(
                    "INSERT INTO areas (nome, tipo, total_uso) VALUES (%s, %s, 1)",
                    (nome_padrao, tipo)
                )
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

    def associar_areas_candidato(self, candidato_id, areas_interesse, areas_atuacao):
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        try:
            # Remove associações anteriores
            cursor.execute(
                "DELETE FROM candidato_areas WHERE candidato_id = %s",
                (candidato_id,)
            )

            # Processa áreas de interesse
            for area in areas_interesse:
                if area and len(str(area).strip()) > 0:
                    try:
                        area_id = self._get_or_create_area(area, 'interesse')
                        cursor.execute(
                            """INSERT INTO candidato_areas 
                               (candidato_id, area_id, tipo) VALUES (%s, %s, 'interesse')""",
                            (candidato_id, area_id)
                        )
                    except Exception as e:
                        print(f"Erro ao associar área de interesse '{area}': {e}")

            # Processa áreas de atuação
            for area in areas_atuacao:
                if area and len(str(area).strip()) > 0:
                    try:
                        area_id = self._get_or_create_area(area, 'atuacao')
                        cursor.execute(
                            """INSERT INTO candidato_areas 
                               (candidato_id, area_id, tipo) VALUES (%s, %s, 'atuacao')""",
                            (candidato_id, area_id)
                        )
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

    def buscar_areas_similares(self, termo, tipo):
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        try:
            # Primeiro tenta encontrar áreas exatas ou similares no profissoes_classes
            areas_similares = set()
            termo_lower = termo.lower()

            # Verifica correspondência exata nas chaves
            for area_padrao, similares in profissoes_classes.items():
                if termo_lower in area_padrao:
                    areas_similares.add(area_padrao)
                # Verifica nos similares
                for similar in similares:
                    if termo_lower in similar:
                        areas_similares.add(area_padrao)
                        break

            # Converte para lista e limita a 5 resultados
            areas_lista = list(areas_similares)[:5]

            # Se não encontrou 5 resultados, busca no banco
            if len(areas_lista) < 5:
                query = """
                SELECT id, nome, total_uso 
                FROM areas 
                WHERE tipo = %s 
                AND LOWER(nome) LIKE %s 
                AND nome NOT IN %s
                ORDER BY total_uso DESC 
                LIMIT %s
                """
                cursor.execute(
                    query,
                    (tipo, f"%{termo_lower}%", tuple(areas_lista) or ('',), 5 - len(areas_lista))
                )
                resultados_banco = cursor.fetchall()

                # Combina os resultados
                resultados_finais = []
                for area in areas_lista:
                    resultados_finais.append({
                        'id': None,  # Será preenchido quando criado no banco
                        'nome': area,
                        'total_uso': 0
                    })
                resultados_finais.extend(resultados_banco)

                return resultados_finais

            return [{'id': None, 'nome': area, 'total_uso': 0} for area in areas_lista]

        except Exception as e:
            print(f"Erro ao buscar áreas similares para '{termo}' do tipo '{tipo}': {e}")
            return []
        finally:
            cursor.close()
            conn.close()