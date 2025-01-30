import openai
import json
import mysql.connector
from datetime import datetime
import re

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
        self.conn = None
        self.cursor = None

    def _get_connection(self):
        try:
            self.conn = mysql.connector.connect(**DB_CONFIG)
            self.cursor = self.conn.cursor(dictionary=True)
        except Exception as e:
            print(f"Erro ao conectar ao banco: {e}")
            raise

    def _close_connection(self):
        try:
            if self.cursor:
                self.cursor.close()
            if self.conn and self.conn.is_connected():
                self.conn.close()
        except Exception as e:
            print(f"Erro ao fechar conexão: {e}")

    def _buscar_profissoes_similares(self):
        """Busca todas as profissões e seus termos similares no banco"""
        try:
            self._get_connection()
            self.cursor.execute("""
                SELECT 
                    nome,
                    descricao,
                    termos_similares,
                    total_uso
                FROM profissoes 
                WHERE total_uso > 0 
                ORDER BY total_uso DESC
            """)
            profissoes = self.cursor.fetchall()

            # Formata os dados para o prompt
            profissoes_info = []
            for prof in profissoes:
                termos = prof['termos_similares'].split(',') if prof['termos_similares'] else []
                termos = [t.strip() for t in termos if t.strip()]  # Limpa termos vazios
                profissoes_info.append({
                    'nome': prof['nome'],
                    'descricao': prof['descricao'] or '',
                    'termos_similares': termos,
                    'frequencia': prof['total_uso']
                })

            return profissoes_info
        except Exception as e:
            print(f"Erro ao buscar profissões: {e}")
            return []
        finally:
            self._close_connection()

    def analisar_curriculo(self, texto):
        try:
            # Busca profissões existentes
            profissoes_existentes = self._buscar_profissoes_similares()
            profissoes_prompt = ""

            if profissoes_existentes:
                profissoes_prompt = "\n\nPROFISSÕES CADASTRADAS:\n"
                for prof in profissoes_existentes:
                    prof_info = (
                        f"- {prof['nome']} (usado {prof['frequencia']} vezes)\n"
                        f"  Similares: {', '.join(prof['termos_similares']) if prof['termos_similares'] else 'nenhum'}\n"
                    )
                    profissoes_prompt += prof_info

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

                        {profissoes_prompt}

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

                            "profissao": {{
                                "nome": "string",
                                "descricao": "string",
                                "termos_similares": ["string"]
                            }},

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

                        IDENTIFICAÇÃO DE PROFISSÕES:
                        1. Primeiro procure nas profissões cadastradas
                        2. Use a mais similar se encontrar
                        3. Se não encontrar, crie nova com termos similares
                        4. Mantenha consistência com as existentes

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
                'pretensao_salarial': dados.get('pretensao_salarial') if isinstance(dados.get('pretensao_salarial'),
                                                                                    (int, float)) else None,
                'disponibilidade': dados.get('disponibilidade', 'imediata'),
                'tipo_contrato': dados.get('tipo_contrato', 'clt'),
                'observacoes_ia': dados.get('observacoes_ia', [])[:3] or ['perfil em análise', 'necessita validação',
                                                                          'requer mais detalhes'],
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

            profissao = {
                'nome': str(dados.get('profissao', {}).get('nome', '')).lower().strip(),
                'descricao': str(dados.get('profissao', {}).get('descricao', '')),
                'termos_relacionados': dados.get('profissao', {}).get('termos_relacionados', [])
            }

            # Arrays
            idiomas = dados.get('idiomas', [])
            areas_interesse = dados.get('areas_interesse', [])
            areas_atuacao = dados.get('areas_atuacao', [])

            dados_validados = {
                'profissional': profissional,
                'faculdade': faculdade,
                'profissao': profissao,
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
                'victor', 'vitor', 'sergio', 'sergio', 'claudio', 'cesar', 'ricardo',
                'mario', 'marcio', 'marcos', 'marcelo', 'miguel', 'michael', 'william',
                'joao paulo', 'jose carlos', 'luiz carlos', 'jean carlos', 'joao pedro',
                'joao victor', 'joao lucas', 'joao marcos', 'joao gabriel', 'joao miguel',
                'enzo', 'valentim', 'theo', 'lorenzo', 'miguel', 'arthur', 'bernardo',
                'heitor', 'davi', 'david', 'theo', 'pedro henrique', 'pietro', 'benjamin',
                'gustavo', 'henrique', 'lucas', 'luis', 'luiz', 'marcos', 'gabriel', 'rafael',
                'john', 'michael', 'william', 'james', 'robert', 'david', 'richard',

                *[nome for nome in [primeiro_nome] if nome.endswith(('son', 'ton', 'ilton', 'ilson', 'anderson'))]
            }

            # Dicionário de nomes femininos comuns no Brasil
            nomes_femininos = {
                'maria', 'ana', 'juliana', 'adriana', 'julia', 'beatriz', 'jessica',
                'fernanda', 'patricia', 'paula', 'alice', 'bruna', 'amanda', 'rosa',
                'carolina', 'mariana', 'vanessa', 'camila', 'daniela', 'isabela', 'isabel',
                'larissa', 'leticia', 'sandra', 'priscila', 'carla', 'monica', 'angela',
                'maria jose', 'ana maria', 'ana paula', 'maria helena', 'maria eduarda',
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

    def _criar_mensagem_usuario(self, texto):
        return {
            "role": "user",
            "content": f"""
            Analise o currículo e retorne um JSON EXATAMENTE com esta estrutura:

            {{
                "nome": "string",
                "email": "string",
                "telefone": "string",
                "endereco": "string",
                "portfolio_url": "string",
                "linkedin_url": "string",
                "github_url": "string",
                "genero": "string",
                "idade": number,
                "pretensao_salarial": number,
                "disponibilidade": "string",
                "tipo_contrato": "string",

                "profissao": {{
                    "nome": "string",
                    "descricao": "string",
                    "termos_relacionados": ["string"] 
                }},

                "faculdade": {{
                    "nome": "string",
                    "cidade": "string",
                    "estado": "string",
                    "pais": "string",
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
                        "nivel_interesse": number
                    }}
                ],

                "areas_atuacao": [
                    {{
                        "nome": "string",
                        "anos_experiencia": number,
                        "ultimo_cargo": "string",
                        "ultima_empresa": "string",
                        "descricao_atividades": "string"
                    }}
                ],

                "observacoes_ia": ["string"],
                "campos_dinamicos": {{}}
            }}

            REGRAS IMPORTANTES:

            1. GÊNERO (obrigatório)
            - Masculino: João, José, Carlos, Antonio, Francisco
            - Feminino: Maria, Ana, Paula, Julia, Sandra
            - Default: "não identificado"

            2. DISPONIBILIDADE (valores válidos)
            {DISPONIBILIDADE}

            3. TIPO_CONTRATO (valores válidos)
            {TIPOS_CONTRATO}

            4. NÍVEIS DE IDIOMA (valores válidos)
            {NIVEIS_IDIOMA}

            5. NÍVEL DE INTERESSE
            - 1: muito baixo
            - 2: baixo
            - 3: médio
            - 4: alto
            - 5: muito alto

            6. REGRAS GERAIS
            - Todo texto em lowercase
            - Campos vazios: "" para texto, null para números
            - Mínimo 3 observações da IA
            - Campos dinâmicos para informações extras do curriculo

            7. OBSERVACÕES IMPORTANTES
            - Se houver erro, retorne a estrutura vazia
           
            **8.SUPER IMPORTANTE PROFISSOES SIMILARES:
            -sempre salvar as profissoes segundo para nao repedir 
            -sempre salvar as areas de interesse e atuacao para nao repetir 
            -sempre salvar as areas de atuação para nao repetir 
            
            9.Sigla estados brasileiros:
            -Sempre coloque as siglas quando houver estado AC, AL, AP, AM, BA, CE, DF, ES, GO, MA, MT, MS, MG, PA, PB, 
            PR, PE, PI, RJ, RN, 
            RS, 
            RO, RR, SC, SP, SE, TO
           
            **10. SUPER IMPORTANTE HABIILIDADES:
            Extrair todas as habilidades técnicas e competências mencionadas
            - Incluir ferramentas, tecnologias, metodologias
            - Normalizar nomes (ex: "Ms Excel" -> "excel")
            - Remover duplicatas
            
            Currículo para análise:
            {texto}
            """
        }

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
                'observacoes_ia': ['dados não processados', 'necessita análise', 'requer validação'],
                'campos_dinamicos': {},
                'habilidades': [],
            },
            'faculdade': {
                'nome': '',
                'cidade': '',
                'estado': 'sempre coloque a sigla do estado ex: SP, RJ, MG ',
                'pais': 'brasil',
                'tipo': ''
            },
            'profissao': {
                'nome': 'profissional',
                'descricao': ''
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
                palavras_ignorar = {'me', 'de', 'mostre', 'liste', 'quero', 'preciso', 'somente',
                                    'apenas', 'pessoas', 'profissionais', 'interessadas', 'interessados',
                                    'em', 'com', 'e', 'ou', 'que', 'tem', 'têm', 'possuem', 'são'}
                termos_busca = [termo for termo in termos if termo not in palavras_ignorar]

                # Cria padrão mais específico juntando os termos
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
                prof.nome as profissao,
                MAX(paa.anos_experiencia) as anos_experiencia,
                GROUP_CONCAT(DISTINCT paa.ultimo_cargo) as ultimo_cargo,
                GROUP_CONCAT(DISTINCT paa.ultima_empresa) as ultima_empresa,
                GROUP_CONCAT(DISTINCT aa.nome) as areas_atuacao,
                GROUP_CONCAT(DISTINCT ai.nome) as areas_interesse,
                p.habilidades,
                GROUP_CONCAT(DISTINCT i.nome ORDER BY i.nome SEPARATOR ', ') as idiomas
            FROM profissionais p
            LEFT JOIN profissoes prof ON p.profissao_id = prof.id
            LEFT JOIN profissionais_areas_atuacao paa ON p.id = paa.profissional_id
            LEFT JOIN areas_atuacao aa ON paa.area_atuacao_id = aa.id
            LEFT JOIN profissionais_areas_interesse pai ON p.id = pai.profissional_id
            LEFT JOIN areas_interesse ai ON pai.area_interesse_id = ai.id
            LEFT JOIN profissionais_idiomas pi ON p.id = pi.profissional_id
            LEFT JOIN idiomas i ON pi.idioma_id = i.id
            WHERE (
                prof.nome REGEXP '{0}'
                OR paa.ultimo_cargo REGEXP '{0}'
                OR aa.nome REGEXP '{0}'
                OR ai.nome REGEXP '{0}'
                OR LOWER(paa.descricao_atividades) REGEXP '{0}'
                OR JSON_CONTAINS(LOWER(p.habilidades), '"{0}"')
            )
            GROUP BY p.id, p.nome, p.email, p.github_url, p.linkedin_url, p.portfolio_url, prof.nome, p.habilidades
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
                prof.nome as profissao,
                MAX(paa.anos_experiencia) as anos_experiencia,
                GROUP_CONCAT(DISTINCT paa.ultimo_cargo) as ultimo_cargo,
                GROUP_CONCAT(DISTINCT paa.ultima_empresa) as ultima_empresa,
                GROUP_CONCAT(DISTINCT aa.nome) as areas_atuacao,
                GROUP_CONCAT(DISTINCT ai.nome) as areas_interesse,
                p.habilidades,
                GROUP_CONCAT(DISTINCT i.nome ORDER BY i.nome SEPARATOR ', ') as idiomas
            FROM profissionais p
            LEFT JOIN profissoes prof ON p.profissao_id = prof.id
            LEFT JOIN profissionais_areas_atuacao paa ON p.id = paa.profissional_id
            LEFT JOIN areas_atuacao aa ON paa.area_atuacao_id = aa.id
            LEFT JOIN profissionais_areas_interesse pai ON p.id = pai.profissional_id
            LEFT JOIN areas_interesse ai ON pai.area_interesse_id = ai.id
            LEFT JOIN profissionais_idiomas pi ON p.id = pi.profissional_id
            LEFT JOIN idiomas i ON pi.idioma_id = i.id
            WHERE TRUE
            GROUP BY p.id, p.nome, p.email, p.github_url, p.linkedin_url, p.portfolio_url, prof.nome, p.habilidades
            """