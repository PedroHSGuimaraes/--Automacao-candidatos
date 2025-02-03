import openai
import json
import re
from datetime import datetime

from src.config.config_settings import (
    OPENAI_KEY,
    NIVEIS_IDIOMA,
    TIPOS_CONTRATO,
    DISPONIBILIDADE,
    DB_CONFIG
)
class GPTService:
    def __init__(self):
        openai.api_key = OPENAI_KEY
        self.system_message = {
            "role": "system",
            "content": "Você é um analisador avançado de currículos especializado em extrair informações estruturadas."
        }

    def analisar_curriculo(self, texto):
        try:
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

    def _converter_strings_para_lowercase(self, obj):
        if isinstance(obj, str):
            return obj.lower()
        elif isinstance(obj, dict):
            return {key: self._converter_strings_para_lowercase(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._converter_strings_para_lowercase(item) for item in obj]
        return obj

    def _validar_dados(self, dados):
        estrutura_padrao = self._get_estrutura_vazia()
        dados_validados = {}

        try:
            profissional = {
                'nome': str(dados.get('nome', '')),
                'email': str(dados.get('email', '')),
                'telefone': str(dados.get('telefone', '')),
                'endereco': str(dados.get('endereco', '')),
                'portfolio_url': str(dados.get('portfolio_url', '')),
                'linkedin_url': str(dados.get('linkedin_url', '')),
                'github_url': str(dados.get('github_url', '')),
                'genero': self._inferir_genero(str(dados.get('nome', ''))),
                'idade': dados.get('idade') if isinstance(dados.get('idade'), (int, float)) else None,
                'pretensao_salarial': dados.get('pretensao_salarial') if isinstance(dados.get('pretensao_salarial'), (int, float)) else None,
                'disponibilidade': dados.get('disponibilidade', 'imediata'),
                'tipo_contrato': dados.get('tipo_contrato', 'clt'),
                'cargo_atual': dados.get('cargo_atual', ''),
                'observacoes_ia': dados.get('observacoes_ia', [])[:3] or ['perfil em análise', 'necessita validação', 'requer mais detalhes'],
                'habilidades': dados.get('habilidades', []) if isinstance(dados.get('habilidades'), list) else [],
                'campos_dinamicos': dados.get('campos_dinamicos', {}) or {'observacoes': 'dados em análise'}
            }

            if profissional['disponibilidade'] not in DISPONIBILIDADE:
                profissional['disponibilidade'] = 'imediata'
            if profissional['tipo_contrato'] not in TIPOS_CONTRATO:
                profissional['tipo_contrato'] = 'clt'

            # Faculdade
            faculdade = {
                'nome': str(dados.get('faculdade', {}).get('nome', '')),
                'cidade': str(dados.get('faculdade', {}).get('cidade', '')),
                'estado': str(dados.get('faculdade', {}).get('estado', '')),
                'pais': str(dados.get('faculdade', {}).get('pais', 'brasil')),
                'tipo': str(dados.get('faculdade', {}).get('tipo', ''))
            }

            # Arrays
            idiomas = dados.get('idiomas', [])
            areas_interesse = dados.get('areas_interesse', [])
            areas_atuacao = dados.get('areas_atuacao', [])

            dados_validados = {
                'profissional': profissional,
                'faculdade': faculdade,
                'idiomas': idiomas,
                'areas_interesse': areas_interesse,
                'areas_atuacao': areas_atuacao
            }

            return dados_validados

        except Exception as e:
            print(f"Erro na validação: {e}")
            return estrutura_padrao

    def _inferir_genero(self, nome):
        try:
            if not nome or not isinstance(nome, str):
                return 'não identificado'

            import unicodedata
            primeiro_nome = unicodedata.normalize('NFKD', nome.split()[0]) \
                .encode('ASCII', 'ignore') \
                .decode('ASCII') \
                .lower()

            nomes_masculinos = {
                'joao', 'jose', 'antonio', 'francisco', 'carlos', 'paulo', 'pedro', 'lucas',
                'luiz', 'luis', 'marcos', 'gabriel', 'rafael', 'daniel', 'marcelo', 'bruno',
                'eduardo', 'felipe', 'rodrigo', 'manoel', 'manuel', 'jorge', 'andre', 'raul',
                'victor', 'vitor', 'sergio', 'claudio', 'cesar', 'ricardo', 'mario', 'marcio',
                'marcos', 'marcelo', 'miguel', 'michael', 'william', 'john', 'james', 'robert',
                'david', 'richard', 'thomas', 'charles', 'joseph', 'christopher', 'daniel',
                *[nome for nome in [primeiro_nome] if nome.endswith(('son', 'ton', 'ilton', 'ilson'))]
            }

            nomes_femininos = {
                'maria', 'ana', 'juliana', 'adriana', 'julia', 'beatriz', 'jessica',
                'fernanda', 'patricia', 'paula', 'alice', 'bruna', 'amanda', 'rosa',
                'carolina', 'mariana', 'vanessa', 'camila', 'daniela', 'isabela', 'isabel',
                'larissa', 'leticia', 'sandra', 'priscila', 'carla', 'monica', 'angela',
                'sophia', 'helena', 'valentina', 'cecilia', 'clara', 'iris', 'aurora',
                'bella', 'maya', 'maia', 'isis', 'lara', 'agnes', 'louise', 'luiza',
                'jennifer', 'elizabeth', 'sarah', 'michelle', 'emma', 'olivia', 'lisa',
                *[nome for nome in [primeiro_nome] if nome.endswith(('ana', 'ela', 'ila', 'ina'))]
            }

            if primeiro_nome in nomes_masculinos:
                return 'masculino'
            elif primeiro_nome in nomes_femininos:
                return 'feminino'
            elif primeiro_nome.endswith(('son', 'ton', 'ilton', 'ilson')):
                return 'masculino'
            elif primeiro_nome.endswith(('a', 'ana', 'ela', 'ila', 'ina')):
                if primeiro_nome not in ['joshua', 'luca', 'nokia', 'costa', 'moura']:
                    return 'feminino'

            return 'não identificado'

        except Exception as e:
            print(f"Erro ao inferir gênero do nome '{nome}': {e}")
            return 'não identificado'

    def _get_estrutura_vazia(self):
        return {
            'profissional': {
                'nome': '',
                'email': '',
                'telefone': '',
                'endereco': '',
                'portfolio_url': '',
                'linkedin_url': '',
                'github_url': '',
                'genero': 'não identificado',
                'idade': None,
                'pretensao_salarial': None,
                'disponibilidade': 'imediata',
                'tipo_contrato': 'clt',
                'cargo_atual': '',
                'observacoes_ia': ['dados não processados', 'necessita análise', 'requer validação'],
                'campos_dinamicos': {},
                'habilidades': [],
            },
            'faculdade': {
                'nome': '',
                'cidade': '',
                'estado': '',
                'pais': 'brasil',
                'tipo': ''
            },
            'idiomas': [],
            'areas_interesse': [],
            'areas_atuacao': []
        }

    def gerar_query_sql(self, prompt, schema=None):
        try:
            # Padrões específicos para áreas comuns
            padroes_especificos = {
                'tecnologia': {
                    'back_end': r'back[-\s]?end|backend|desenvolvimento\s*back[-\s]?end',
                    'front_end': r'front[-\s]?end|frontend|desenvolvimento\s*front[-\s]?end',
                    'full_stack': r'full[-\s]?stack|fullstack|desenvolvimento\s*full[-\s]?stack',
                    'mobile': r'mobile|android|ios|desenvolvimento\s*mobile',
                    'web': r'desenvolvimento\s*web|web\s*developer',
                    'dados': r'cientista\s*de\s*dados|analista\s*de\s*dados|data\s*science',
                    'devops': r'devops|dev[-\s]?ops|engenheiro\s*devops',
                    'qa': r'qa|quality\s*assurance|teste\s*de\s*software'
                },
                'logistica': {
                    'motorista': r'motorist[ao]|condutor[a]?|operator\s*de\s*veículos?',
                    'transportador': r'transportador[a]?|entregador[a]?',
                    'operador': r'operador[a]?\s*de\s*(máquina|empilhadeira|guindaste)',
                    'conferente': r'conferente|auxiliar\s*de\s*logística'
                },
                'saude': {
                    'medico': r'médic[oa]|dr\.|doutor[a]?',
                    'enfermeiro': r'enfermeir[oa]|técnic[oa]\s*de\s*enfermagem',
                    'dentista': r'dentista|odontolog[oa]',
                    'fisioterapeuta': r'fisioterapeuta|fisioterap[êe]utic[oa]'
                },
                'educacao': {
                    'professor': r'professor[a]?|docente|educador[a]?',
                    'coordenador': r'coordenador[a]?\s*pedagógic[oa]?',
                    'diretor': r'diretor[a]?\s*escolar'
                }
            }

            # Processa o prompt
            prompt_lower = prompt.lower()
            padrao_encontrado = None

            # Primeiro tenta encontrar padrões específicos
            for area, padroes in padroes_especificos.items():
                for tipo, padrao in padroes.items():
                    if re.search(padrao, prompt_lower):
                        padrao_encontrado = padrao
                        break
                if padrao_encontrado:
                    break

            # Se não encontrar padrão específico, cria um mais preciso com as palavras-chave
            if not padrao_encontrado:
                termos = prompt_lower.split()
                palavras_ignorar = {
                    'me', 'de', 'mostre', 'liste', 'quero', 'preciso', 'somente',
                    'apenas', 'pessoas', 'profissionais', 'interessadas', 'interessados',
                    'em', 'com', 'e', 'ou', 'que', 'tem', 'têm', 'possuem', 'são', 'como'
                }
                termos_busca = [termo for termo in termos if termo not in palavras_ignorar]
                padrao_encontrado = r'\b(' + '|'.join(termos_busca) + r')\b'

            # Monta a query base
            query_base = """
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
                LOWER(p.cargo_atual) REGEXP '{0}'
                OR LOWER(paa.ultimo_cargo) REGEXP '{0}'
                OR LOWER(aa.nome) REGEXP '{0}'
                OR LOWER(ai.nome) REGEXP '{0}'
                OR LOWER(paa.descricao_atividades) REGEXP '{0}'
                OR JSON_CONTAINS(LOWER(p.habilidades), '"{0}"')
            )
            GROUP BY p.id, p.nome, p.email, p.github_url, p.linkedin_url, p.portfolio_url, p.cargo_atual, p.habilidades
            """.format(padrao_encontrado)

            return query_base

        except Exception as e:
            print(f"Erro ao gerar query: {e}")
            print("Prompt original:", prompt)
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
            GROUP BY p.id, p.nome, p.email, p.github_url, p.linkedin_url, p.portfolio_url, p.cargo_atual, p.habilidades
            """
