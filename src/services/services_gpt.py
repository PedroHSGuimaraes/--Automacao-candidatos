import openai
import google.generativeai as genai
import json
import re
from datetime import datetime

from src.config.config_settings import (
    OPENAI_KEY,
    GEMINI_KEY,
    NIVEIS_IDIOMA,
    TIPOS_CONTRATO,
    DISPONIBILIDADE,
    DB_CONFIG
)
from src.services.services_data import DataService


class GPTService:
    def __init__(self, model="gpt"):
        self.model = model
        if model == "gpt":
            openai.api_key = OPENAI_KEY
        else:
            genai.configure(api_key=GEMINI_KEY)
            self.gemini_model = genai.GenerativeModel('gemini-pro')

        self.system_message = {
            "role": "system",
            "content": "Você é um analisador avançado de currículos especializado em extrair informações estruturadas."
        }
        self.data_service = DataService()

    def analisar_curriculo(self, texto):
        try:
            if self.model == "gpt":
                response = openai.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": """Você é um analisador especializado em extrair informações 
                            estruturadas de currículos e retornar APENAS JSON válido."""
                        },
                        {
                            "role": "user",
                            "content": f"""
                            IMPORTANTE: Retorne APENAS um JSON válido sem nenhum texto adicional.

                            Analise o currículo e retorne este JSON:

                            {{
                                "nome": "string",
                                "email": "string",
                                "telefone": "string",
                                "endereco": "string",
                                "portfolio_url": "string",
                                "linkedin_url": "string",
                                "github_url": "string",
                                "genero": "string",
                                "idade": null,
                                "pretensao_salarial": null,
                                "disponibilidade": "string",
                                "tipo_contrato": "string",
                                "habilidades": ["string"],
                                "cargo_atual": "string",

                                "faculdade": {{
                                    "nome": "string",
                                    "cidade": "string",
                                    "estado": "string",
                                    "pais": "brasil",
                                    "tipo": "string"
                                }},

                                "idiomas": [
                                    {{
                                        "nome": "string",
                                        "nivel": "string",
                                        "certificacao": "string"
                                    }}
                                ],

                                "areas_interesse": [
                                    {{
                                        "nome": "string",
                                        "nivel_interesse": 3,
                                        "termos_similares": ["string"]
                                    }}
                                ],

                                "areas_atuacao": [
                                    {{
                                        "nome": "string",
                                        "anos_experiencia": 0,
                                        "ultimo_cargo": "string",
                                        "ultima_empresa": "string",
                                        "descricao_atividades": "string",
                                        "termos_similares": ["string"]
                                    }}
                                ],

                                "observacoes_ia": ["string"],
                                "campos_dinamicos": {{}}
                            }}

                            REGRAS:
                            1. GÊNERO: masculino, feminino ou não identificado
                            2. DISPONIBILIDADE: {DISPONIBILIDADE}
                            3. TIPO_CONTRATO: {TIPOS_CONTRATO}
                            4. IDIOMAS (níveis): {NIVEIS_IDIOMA}
                            5. INTERESSE: 1 a 5
                            6. ESTADOS: usar siglas (SP, RJ, MG...)

                            VALIDAÇÕES:
                            1. Todo texto em lowercase
                            2. Arrays vazios = []
                            3. Objetos vazios = {{}}
                            4. Textos vazios = ""
                            5. Números vazios = null
                            6. Mínimo 3 observações da IA

                            EXTRAÇÃO DE HABILIDADES:
                            1. Extrair todas habilidades técnicas
                            2. Incluir ferramentas e tecnologias
                            3. Normalizar nomes (ex: "Ms Excel" -> "excel")
                            4. Remover duplicatas
                            5. Identificar nível quando possível

                            Currículo para análise:
                            {texto}
                            """
                        }
                    ],
                    temperature=0.1,
                    max_tokens=2000
                )
                content = response.choices[0].message.content.strip()
            else:
                response = self.gemini_model.generate_content(
                    f"""Você é um analisador especializado em extrair informações estruturadas de currículos.
                    Retorne APENAS o JSON válido sem nenhum texto adicional.

                    [restante do prompt igual ao do GPT...]
                    """
                )
                content = response.text.strip()

            content = content.replace('```json', '').replace('```', '').strip()

            try:
                dados = json.loads(content)
            except json.JSONDecodeError as e:
                print(f"Erro no JSON: {e}")
                print(f"Conteúdo recebido: {content[:500]}...")
                return self._get_estrutura_vazia()

            dados_validados = self._validar_dados(dados)
            dados_validados = self._converter_strings_para_lowercase(dados_validados)

            return dados_validados

        except Exception as e:
            print(f"Erro na análise do currículo: {e}")
            return self._get_estrutura_vazia()

    def gerar_query_sql(self, prompt, schema=None):
        try:
            # 1. Primeiro fazemos análise prévia do banco
            analise_previa = """
            SELECT
                (SELECT GROUP_CONCAT(DISTINCT cargo_atual) FROM profissionais WHERE cargo_atual IS NOT NULL) as cargos,
                (SELECT GROUP_CONCAT(DISTINCT nome) FROM areas_atuacao) as areas_atuacao_nomes,
                (SELECT GROUP_CONCAT(DISTINCT descricao) FROM areas_atuacao) as areas_atuacao_descricoes,
                (SELECT GROUP_CONCAT(DISTINCT nome) FROM idiomas) as idiomas_nomes,
                (SELECT GROUP_CONCAT(DISTINCT codigo) FROM idiomas) as idiomas_codigos,
                (SELECT GROUP_CONCAT(DISTINCT nivel) FROM profissionais_idiomas) as niveis_idiomas,
                (SELECT GROUP_CONCAT(DISTINCT ultimo_cargo) FROM profissionais_areas_atuacao) as ultimos_cargos,
                (SELECT GROUP_CONCAT(DISTINCT nome) FROM generos) as generos_nomes,
                (SELECT GROUP_CONCAT(DISTINCT nome) FROM areas_interesse) as areas_interesse_nomes,
                (SELECT GROUP_CONCAT(DISTINCT descricao) FROM areas_interesse) as areas_interesse_descricoes,
                (SELECT GROUP_CONCAT(DISTINCT nome) FROM faculdades) as faculdades_nomes
            """

            dados_contexto = self.data_service.executar_query(analise_previa)

            # 2. Consultamos a IA com o schema detalhado
            if self.model == "gpt":
                response = openai.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": f"""Você é um especialista em SQL. Use EXATAMENTE estes nomes de tabelas e colunas:

                            profissionais AS p:
                            - id, nome, email, cargo_atual, github_url, linkedin_url, portfolio_url, habilidades, faculdade_id, genero_id, idioma_principal_id, nivel_idioma_principal, pdf_curriculo, idade, pretensao_salarial, disponibilidade, tipo_contrato, data_criacao, ultima_atualizacao, observacoes_ia, campos_dinamicos, habilidades

                            areas_atuacao AS aa:
                            - id, nome, descricao, total_uso, ultima_atualizacao, termos_similares, data_criacao

                            profissionais_areas_atuacao AS paa:
                            - profissional_id, area_atuacao_id, anos_experiencia, ultimo_cargo, ultima_empresa, data_inicio, data_fim, descricao_atividades, data_criacao

                            areas_interesse AS ai:
                            - id, nome, descricao, total_uso, ultima_atualizacao, termos_similares, data_criacao

                            profissionais_areas_interesse AS pai:
                            - profissional_id, area_interesse_id, nivel_interesse, data_criacao

                            idiomas AS i:
                            - id, nome, codigo, data_criacao

                            profissionais_idiomas AS pi:
                            - profissional_id, idioma_id, nivel, certificacao, data_certificacao, data_criacao

                            faculdades AS f:
                            - id, nome, cidade, estado, pais, tipo, ranking, data_criacao

                            generos AS g:
                            - id, nome, descricao, data_criacao

                            Dados existentes no banco:
                            {dados_contexto[0] if dados_contexto else ''}"""
                        },
                        {
                            "role": "user",
                            "content": f"""Gere APENAS uma query MySQL para: {prompt}
                            Use SOMENTE os nomes de colunas especificados acima.
                            Use a sintaxe AS para aliases de tabela.
                            Retorne APENAS a query MYSQL, sem explicações."""
                        }
                    ],
                    temperature=0.1
                )
                query = response.choices[0].message.content.strip()
            else:
                # Similar para Gemini
                response = self.gemini_model.generate_content(f"""[schema detalhado e prompt]""")
                query = response.text.strip()

            # Limpa a query
            query = query.replace('```sql', '').replace('```', '').strip()

            # Valida se a query é segura
            query_lower = query.lower()
            if any(word in query_lower for word in ['drop', 'delete', 'update', 'insert', 'truncate']):
                raise ValueError("Query não permitida")

            # Se nenhuma query válida for gerada, usa a query padrão
            if not query or 'select' not in query_lower:
                return self._get_query_padrao()

            return query

        except Exception as e:
            print(f"Erro ao gerar query: {e}")
            return self._get_query_padrao()

    def _get_query_padrao(self):
        return """
        SELECT DISTINCT
            p.id,
            p.nome,
            p.email,
            p.github_url,
            p.linkedin_url,
            p.portfolio_url,
            p.cargo_atual,
            MAX(paa.anos_experiencia) as anos_experiencia,
            GROUP_CONCAT(DISTINCT paa.ultimo_cargo) as ultimo_cargo,
            GROUP_CONCAT(DISTINCT paa.ultima_empresa) as ultima_empresa,
            GROUP_CONCAT(DISTINCT aa.nome) as areas_atuacao,
            GROUP_CONCAT(DISTINCT ai.nome) as areas_interesse,
            p.habilidades,
            GROUP_CONCAT(DISTINCT i.nome ORDER BY i.nome SEPARATOR ', ') as idiomas
        FROM profissionais p
        LEFT JOIN profissionais_areas_atuacao paa ON p.id = paa.profissional_id
        LEFT JOIN areas_atuacao aa ON paa.area_atuacao_id = aa.id
        LEFT JOIN profissionais_areas_interesse pai ON p.id = pai.profissional_id
        LEFT JOIN areas_interesse ai ON pai.area_interesse_id = ai.id
        LEFT JOIN profissionais_idiomas pi ON p.id = pi.profissional_id
        LEFT JOIN idiomas i ON pi.idioma_id = i.id
        WHERE p.linkedin_url IS NOT NULL AND p.linkedin_url != ''
        GROUP BY p.id, p.nome, p.email, p.github_url, p.linkedin_url, p.portfolio_url, p.cargo_atual, p.habilidades
        """