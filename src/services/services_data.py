# src/services/services_data.py
from datetime import datetime
import json
import mysql.connector
from src.database.database_connection import DatabaseConnection
from src.config.config_settings import DB_CONFIG
from src.services.services_area import AreaService


class DataService:
    def __init__(self):
        self.area_service = AreaService()

    def executar_query(self, query):
        conn = None
        cursor = None
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query)
            resultados = cursor.fetchall()

            # Processa os resultados
            if resultados:
                for resultado in resultados:
                    for campo, valor in resultado.items():
                        if isinstance(valor, str):
                            try:
                                resultado[campo] = json.loads(valor)
                            except json.JSONDecodeError:
                                pass

            return resultados

        except Exception as e:
            print(f"Erro ao executar query: {str(e)}")
            print(f"Query tentada: {query}")
            raise Exception(f"Erro ao executar query: {str(e)}")
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()

    def buscar_candidatos(self):
        try:
            query = """
            SELECT c.*,
                   GROUP_CONCAT(DISTINCT CASE WHEN ca.tipo = 'interesse' THEN a.nome END) as areas_interesse_nomes,
                   GROUP_CONCAT(DISTINCT CASE WHEN ca.tipo = 'atuacao' THEN a.nome END) as areas_atuacao_nomes
            FROM candidatos c
            LEFT JOIN candidato_areas ca ON c.id = ca.candidato_id
            LEFT JOIN areas a ON ca.area_id = a.id
            GROUP BY c.id
            ORDER BY c.data_criacao DESC
            """
            return self.executar_query(query)
        except Exception as e:
            raise Exception(f"Erro ao buscar candidatos: {e}")

    def salvar_candidato(self, dados, texto_pdf):
        conn = None
        cursor = None
        try:
            # Normaliza os dados
            dados = self._normalize_data(dados)

            # Prepara áreas como JSON
            areas_interesse = json.dumps(dados['experiencia'].get('areas_interesse', []))
            areas_atuacao = json.dumps(dados['experiencia'].get('areas_atuacao', []))

            query = """
            INSERT INTO candidatos (
                nome, email, genero, idade, instituto_formacao, curso, periodo,
                tempo_experiencia, ultima_experiencia, todas_experiencias,
                habilidades, linkedin, github, telefone, data_criacao, pdf_conteudo,
                observacoes_ia, campos_dinamicos, areas_interesse, areas_atuacao
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                dados['experiencia']['ultima_experiencia'],
                json.dumps(dados['experiencia']['todas_experiencias']),
                json.dumps(dados['habilidades']),
                dados['contato']['linkedin'],
                dados['contato']['github'],
                dados['contato']['telefone'],
                datetime.now(),
                texto_pdf,
                json.dumps(dados.get('observacoes_ia', [])),
                json.dumps(dados.get('campos_dinamicos', {})),
                areas_interesse,
                areas_atuacao
            )

            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, valores)
            candidato_id = cursor.lastrowid
            conn.commit()

            # Associa áreas ao candidato
            self.area_service.associar_areas_candidato(
                candidato_id,
                dados['experiencia'].get('areas_interesse', []),
                dados['experiencia'].get('areas_atuacao', [])
            )

            return True
        except Exception as e:
            print(f"Erro detalhado: {str(e)}")
            raise Exception(f"Erro ao salvar candidato: {str(e)}")
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()

    def _normalize_data(self, dados):
        """Normaliza os dados para garantir a estrutura correta"""
        template = self._get_empty_structure()

        try:
            normalized = {
                "dados_basicos": {
                    "nome": str(dados["dados_basicos"].get("nome", "")),
                    "email": str(dados["dados_basicos"].get("email", "")),
                    "genero": str(dados["dados_basicos"].get("genero", "")),
                    "idade": dados["dados_basicos"].get("idade")
                },
                "formacao": {
                    "instituto_formacao": str(
                        dados["formacao"].get("instituto_formacao") or dados["formacao"].get("instituto", "")),
                    "curso": str(dados["formacao"].get("curso", "")),
                    "periodo": str(dados["formacao"].get("periodo", ""))
                },
                "experiencia": {
                    "tempo_experiencia": float(
                        dados["experiencia"].get("tempo_experiencia") or dados["experiencia"].get("tempo_total", 0)),
                    "areas_interesse": list(dados["experiencia"].get("areas_interesse", [])),
                    "areas_atuacao": list(dados["experiencia"].get("areas_atuacao", [])),
                    "ultima_experiencia": str(
                        dados["experiencia"].get("ultima_experiencia") or dados["experiencia"].get("ultima_exp", "")),
                    "todas_experiencias": list(
                        dados["experiencia"].get("todas_experiencias") or dados["experiencia"].get("todas_exp", []))
                },
                "habilidades": list(dados.get("habilidades", [])),
                "contato": {
                    "linkedin": str(dados["contato"].get("linkedin", "")),
                    "github": str(dados["contato"].get("github", "")),
                    "telefone": str(dados["contato"].get("telefone", ""))
                },
                "observacoes_ia": list(dados.get("observacoes_ia") or dados.get("observacoes", [])),
                "campos_dinamicos": dict(dados.get("campos_dinamicos", {}))
            }
            return normalized
        except Exception as e:
            print(f"Erro na normalização dos dados: {e}")
            print("Dados recebidos:", json.dumps(dados, indent=2))
            return template

    def _get_empty_structure(self):
        return {
            "dados_basicos": {
                "nome": "",
                "email": "",
                "genero": "",
                "idade": None
            },
            "formacao": {
                "instituto_formacao": "",
                "curso": "",
                "periodo": ""
            },
            "experiencia": {
                "tempo_experiencia": 0,
                "areas_interesse": [],
                "areas_atuacao": [],
                "ultima_experiencia": "",
                "todas_experiencias": []
            },
            "habilidades": [],
            "contato": {
                "linkedin": "",
                "github": "",
                "telefone": ""
            },
            "observacoes_ia": [],
            "campos_dinamicos": {}
        }