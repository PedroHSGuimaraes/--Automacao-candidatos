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
            prompt_lower = prompt.lower()
            termos = prompt_lower.split()

            # Remove palavras comuns que não ajudam na busca
            palavras_ignorar = {
                'me', 'de', 'mostre', 'liste', 'quero', 'preciso', 'somente',
                'apenas', 'pessoas', 'profissionais', 'interessadas', 'interessados',
                'em', 'com', 'e', 'ou', 'que', 'tem', 'têm', 'possuem', 'são', 'como',
                'quem', 'tem', 'experiência', 'experiencia', 'trabalha', 'trabalhou'
            }

            termos_busca = [termo for termo in termos if termo not in palavras_ignorar]

            # Constrói a condição de busca mais específica
            padrao_regexp = []
            for i in range(len(termos_busca)):
                # Tenta combinar termos adjacentes para busca mais precisa
                if i < len(termos_busca) - 1:
                    termo_composto = f"{termos_busca[i]}.*{termos_busca[i + 1]}"
                    padrao_regexp.append(termo_composto)
                padrao_regexp.append(termos_busca[i])

            padrao_final = '|'.join(padrao_regexp)

            query = """
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
            WHERE (
                (
                    LOWER(p.cargo_atual) REGEXP '{0}'
                    OR LOWER(paa.ultimo_cargo) REGEXP '{0}'
                    OR LOWER(aa.nome) REGEXP '{0}'
                    OR LOWER(paa.descricao_atividades) REGEXP '{0}'
                )
                AND (
                    LOWER(p.cargo_atual) LIKE '%{1}%'
                    OR LOWER(paa.ultimo_cargo) LIKE '%{1}%'
                    OR LOWER(aa.nome) LIKE '%{1}%'
                    OR LOWER(paa.descricao_atividades) LIKE '%{1}%'
                    OR JSON_UNQUOTE(p.habilidades) LIKE '%{1}%'
                )
            )
            GROUP BY p.id, p.nome, p.email, p.github_url, p.linkedin_url, p.portfolio_url, p.cargo_atual, p.habilidades
            HAVING 
                LOWER(ultimo_cargo) LIKE '%{1}%'
                OR LOWER(areas_atuacao) LIKE '%{1}%'
            ORDER BY anos_experiencia DESC
            """.format(padrao_final, termos_busca[-1] if termos_busca else '')

            return query

        except Exception as e:
            print(f"Erro ao gerar query: {e}")
            return self._get_query_padrao()