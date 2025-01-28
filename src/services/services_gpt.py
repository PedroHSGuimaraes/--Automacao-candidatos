import openai
import json
import re
from datetime import datetime
from src.config.config_settings import OPENAI_KEY, NIVEIS_IDIOMA, TIPOS_CONTRATO, DISPONIBILIDADE, SQL_SCHEMA


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
                    self.system_message,
                    self._criar_mensagem_usuario(texto)
                ],
                temperature=0.1
            )

            content = response.choices[0].message.content.strip()

            # Remove marcações de código
            content = content.replace("```json", "").replace("```", "").strip()

            # Tenta fazer o parse do JSON
            try:
                dados = json.loads(content)
            except json.JSONDecodeError:
                print("Erro ao fazer parse do JSON")
                return self._get_estrutura_vazia()

            # Valida e normaliza os dados
            dados_validados = self._validar_dados(dados)

            # Converte strings para lowercase
            dados_validados = self._converter_strings_para_lowercase(dados_validados)

            return dados_validados

        except Exception as e:
            print(f"Erro na análise do currículo: {e}")
            return self._get_estrutura_vazia()

    def _converter_strings_para_lowercase(self, obj):
        """
        Converte apenas strings para lowercase, mantendo a estrutura dos objetos
        """
        if isinstance(obj, str):
            return obj.lower()
        elif isinstance(obj, dict):
            return {key: self._converter_strings_para_lowercase(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._converter_strings_para_lowercase(item) for item in obj]
        return obj

    def _validar_dados(self, dados):
        """
        Valida e estrutura os dados extraídos
        """
        estrutura_padrao = self._get_estrutura_vazia()
        dados_validados = {}

        try:
            # Dados do profissional
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
                'campos_dinamicos': dados.get('campos_dinamicos', {}) or {'observacoes': 'dados em análise'}
            }

            # Ajusta disponibilidade e tipo de contrato para valores válidos
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

            # Profissão
            profissao = {
                'nome': str(dados.get('profissao', {}).get('nome', 'profissional')),
                'descricao': str(dados.get('profissao', {}).get('descricao', ''))
            }

            # Arrays
            idiomas = dados.get('idiomas', [])
            areas_interesse = dados.get('areas_interesse', [])
            areas_atuacao = dados.get('areas_atuacao', [])

            # Monta estrutura final
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
        """
        Infere o gênero com base no primeiro nome
        """
        try:
            nomes_masculinos = ['joao', 'jose', 'carlos', 'paulo', 'pedro', 'antonio',
                                'francisco', 'adenilton', 'alexandre', 'anderson']
            nomes_femininos = ['maria', 'ana', 'paula', 'julia', 'sandra', 'juliana']

            primeiro_nome = nome.lower().split()[0] if nome else ''

            if primeiro_nome in nomes_masculinos:
                return 'masculino'
            elif primeiro_nome in nomes_femininos:
                return 'feminino'
            return 'não identificado'
        except:
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
                    "descricao": "string"
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
            - Campos dinâmicos para informações extras

            Currículo para análise:
            {texto}
            """
        }

    def _get_estrutura_vazia(self):
        """
        Retorna a estrutura padrão com campos vazios
        """
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
                'campos_dinamicos': {'status': 'pendente análise'}
            },
            'faculdade': {
                'nome': '',
                'cidade': '',
                'estado': '',
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

    def gerar_query_sql(self, prompt, schema):
        try:
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """Você é um especialista em SQL que gera queries MySQL válidas usando exatamente estas tabelas:

                        TABELAS PRINCIPAIS:
                        1. profissionais: (dados principais do candidato)
                           - Campos: id, nome, email, telefone, endereco, portfolio_url, linkedin_url, github_url, 
                             profissao_id, faculdade_id, genero_id, idioma_principal_id, nivel_idioma_principal,
                             idade, pretensao_salarial, disponibilidade, tipo_contrato

                        2. profissoes: (cadastro de profissões)
                           - Campos: id, nome, descricao

                        3. generos: (tipos de gênero)
                           - Campos: id, nome, descricao

                        4. faculdades: (instituições de ensino)
                           - Campos: id, nome, cidade, estado, pais, tipo, ranking

                        5. idiomas: (cadastro de idiomas)
                           - Campos: id, nome, codigo

                        6. areas_interesse: (áreas de interesse)
                           - Campos: id, nome, descricao

                        7. areas_atuacao: (áreas de atuação)
                           - Campos: id, nome, descricao

                        REGRAS:
                        1. Use aliases padrão: profissionais p, profissoes prof, generos g, etc
                        2. Use LEFT JOIN para junções
                        3. Retorne apenas a query SQL, sem explicações
                        4. Query deve ser completa em uma única linha (sem quebras)
                        """
                    },
                    {
                        "role": "user",
                        "content": f"""
                        EXEMPLOS DE QUERIES VÁLIDAS:
                        SELECT p.nome, prof.nome as profissao FROM profissionais p LEFT JOIN profissoes prof ON p.profissao_id = prof.id

                        SELECT p.nome, i.nome as idioma, pi.nivel FROM profissionais p LEFT JOIN profissionais_idiomas pi ON p.id = pi.profissional_id LEFT JOIN idiomas i ON pi.idioma_id = i.id

                        SELECT p.nome, aa.nome as area, paa.anos_experiencia FROM profissionais p LEFT JOIN profissionais_areas_atuacao paa ON p.id = paa.profissional_id LEFT JOIN areas_atuacao aa ON paa.area_atuacao_id = aa.id

                        Gere uma query SQL em uma única linha para esta solicitação:
                        {prompt}
                        """
                    }
                ],
                temperature=0.1
            )

            query = response.choices[0].message.content.strip()

            # Limpa a query
            query = query.replace('\n', ' ').replace('\r', ' ')
            query = ' '.join(query.split())  # Remove espaços extras

            # Verifica se é uma query SQL válida
            if not any(query.upper().startswith(word) for word in ['SELECT', 'WITH']):
                raise Exception("Query inválida gerada")

            return query

        except Exception as e:
            print(f"Erro ao gerar query: {e}")
            return None