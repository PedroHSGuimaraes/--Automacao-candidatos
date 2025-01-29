import openai
import json
import re
from datetime import datetime
from src.config.config_settings import OPENAI_KEY, NIVEIS_IDIOMA, TIPOS_CONTRATO, DISPONIBILIDADE, SQL_SCHEMA
from src.utils.classes_profissao import profissoes_classes
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
        Infere o gênero com base no primeiro nome usando regras de nomes brasileiros
        """
        try:
            # Se não tiver nome, retorna não identificado
            if not nome or not isinstance(nome, str):
                return 'não identificado'

            # Normaliza o primeiro nome (remove espaços extras, acentos e converte para minúsculo)
            import unicodedata
            primeiro_nome = unicodedata.normalize('NFKD', nome.split()[0]) \
                .encode('ASCII', 'ignore') \
                .decode('ASCII') \
                .lower()

            # Dicionário de nomes masculinos comuns no Brasil
            nomes_masculinos = {
                # Nomes tradicionais
                'joao', 'jose', 'antonio', 'francisco', 'carlos', 'paulo', 'pedro', 'lucas',
                'luiz', 'luis', 'marcos', 'gabriel', 'rafael', 'daniel', 'marcelo', 'bruno',
                'eduardo', 'felipe', 'rodrigo', 'manoel', 'manuel', 'jorge', 'andre', 'raul',
                'victor', 'vitor', 'sergio', 'sergio', 'claudio', 'cesar', 'ricardo',
                # Nomes compostos comuns
                'joao paulo', 'jose carlos', 'luiz carlos', 'jean carlos', 'joao pedro',
                # Nomes modernos
                'enzo', 'valentim', 'theo', 'lorenzo', 'miguel', 'arthur', 'bernardo',
                'heitor', 'davi', 'david', 'theo', 'pedro henrique', 'pietro', 'benjamin',
                # Variações internacionais
                'john', 'michael', 'william', 'james', 'robert', 'david', 'richard',
                # Sufixos tipicamente masculinos
                *[nome for nome in [primeiro_nome] if nome.endswith(('son', 'ton', 'ilton', 'ilson', 'anderson'))]
            }

            # Dicionário de nomes femininos comuns no Brasil
            nomes_femininos = {
                # Nomes tradicionais
                'maria', 'ana', 'juliana', 'adriana', 'julia', 'beatriz', 'jessica',
                'fernanda', 'patricia', 'paula', 'alice', 'bruna', 'amanda', 'rosa',
                'carolina', 'mariana', 'vanessa', 'camila', 'daniela', 'isabela', 'isabel',
                'larissa', 'leticia', 'sandra', 'priscila', 'carla', 'monica', 'angela',
                # Nomes compostos comuns
                'maria jose', 'ana maria', 'ana paula', 'maria helena', 'maria eduarda',
                # Nomes modernos
                'sophia', 'helena', 'valentina', 'cecilia', 'clara', 'iris', 'aurora',
                'bella', 'maya', 'maia', 'isis', 'lara', 'agnes', 'louise', 'luiza',
                # Variações internacionais
                'jennifer', 'elizabeth', 'sarah', 'michelle', 'emma', 'olivia', 'lisa',
                # Sufixos tipicamente femininos
                *[nome for nome in [primeiro_nome] if nome.endswith(('ana', 'ela', 'ila', 'ina'))]
            }

            # Regras de inferência
            if primeiro_nome in nomes_masculinos:
                return 'masculino'
            elif primeiro_nome in nomes_femininos:
                return 'feminino'
            # Análise de terminações comuns
            elif primeiro_nome.endswith(('son', 'ton', 'ilton', 'ilson')):
                return 'masculino'
            elif primeiro_nome.endswith(('a', 'ana', 'ela', 'ila', 'ina')):
                # Exceções conhecidas para nomes masculinos terminados em 'a'
                if primeiro_nome not in ['joshua', 'luca', 'nokia', 'costa', 'moura']:
                    return 'feminino'

            # Se não conseguiu identificar, retorna não identificado
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
            - Campos dinâmicos para informações extras do curriculo

            7. OBSERVACÕES IMPORTANTES
            - Se houver erro, retorne a estrutura vazia
        **8.Super importante Profissão similares:
            -sempre salvar as profissoes segundo para nao repedir {profissoes_classes}
            -sempre salvar as areas de interesse e atuacao para nao repedir {profissoes_classes}
            -sempre salvar as areas de atuação para nao repedir {profissoes_classes}
            
            
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

    def gerar_query_sql(self, prompt, schema=None):
        """
        Gera uma query SQL com base em uma pergunta em linguagem natural.
        O parâmetro 'schema' é opcional.
        """
        try:
            # Cria a requisição de completions no modelo GPT-4o-mini
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """Você é um analista SQL. Sua função é gerar queries MySQL para buscar dados em um banco com as seguintes tabelas:

                        1. profissionais (p)
                           - id, nome, email, telefone, endereco
                           - portfolio_url, linkedin_url, github_url
                           - profissao_id, faculdade_id, genero_id
                           - idioma_principal_id, nivel_idioma_principal
                           - idade, pretensao_salarial, disponibilidade, tipo_contrato

                        2. profissoes (prof)
                           - id, nome, descricao

                        3. faculdades (f)
                           - id, nome, cidade, estado, pais, tipo

                        4. generos (g)
                           - id, nome [masculino, feminino, não identificado]

                        5. idiomas (i)
                           - id, nome, codigo

                        6. Relacionamentos:
                           - profissionais_idiomas (pi): profissional_id, idioma_id, nivel
                           - profissionais_areas_interesse (pai): profissional_id, area_interesse_id
                           - profissionais_areas_atuacao (paa): profissional_id, area_atuacao_id, anos_experiencia

                        EXEMPLOS:
                        1. "Buscar desenvolvedores que falam inglês"
                           → SELECT DISTINCT p.nome, p.email, prof.nome as profissao, i.nome as idioma, pi.nivel
                             FROM profissionais p
                             LEFT JOIN profissoes prof ON p.profissao_id = prof.id
                             LEFT JOIN profissionais_idiomas pi ON p.id = pi.profissional_id
                             LEFT JOIN idiomas i ON pi.idioma_id = i.id
                             WHERE LOWER(i.nome) = 'inglês'
                             AND LOWER(prof.nome) LIKE '%desenvolv%'

                        2. "Listar profissionais do gênero feminino"
                           → SELECT p.nome, p.email, prof.nome as profissao, g.nome as genero
                             FROM profissionais p
                             LEFT JOIN profissoes prof ON p.profissao_id = prof.id
                             LEFT JOIN generos g ON p.genero_id = g.id
                             WHERE LOWER(g.nome) = 'feminino'
                        """
                    },
                    {
                        "role": "user",
                        "content": f"""
                        Gere uma query SQL para esta pergunta:

                        {prompt}

                        REGRAS:
                        1. Use LEFT JOIN para junções
                        2. Use aliases padrão (p, prof, f, g, i, pi, paa, pai)
                        3. Use LOWER() em comparações de texto
                        4. Sempre inclua nome e email nas colunas
                        5. Use DISTINCT se necessário
                        6. RETORNE APENAS A QUERY, nada mais
                        7. **Nao pode começar com ```sql ou terminar com ``` ou algo do tipo
                        """
                    }
                ],
                temperature=0.1,
                max_tokens=1000
            )

            # Extrai e limpa a resposta
            query = response.choices[0].message.content.strip()
            print("Query gerada:", query)  # Log para debug

            # Remove quebras de linha e espaços extras
            query = query.replace('\n', ' ').replace('\r', ' ')
            query = ' '.join(query.split())

            # Validação básica
            query_upper = query.upper()
            if not query_upper.startswith('SELECT'):
                print("Query não começa com SELECT:", query)
                raise Exception("Query deve começar com SELECT")

            if 'FROM' not in query_upper:
                print("Query não contém FROM:", query)
                raise Exception("Query deve conter FROM")

            # Verifica a presença de palavras-chave obrigatórias
            required_keywords = ['SELECT', 'FROM', 'PROFISSIONAIS']
            missing_keywords = [word for word in required_keywords if word not in query_upper]
            if missing_keywords:
                print(f"Palavras-chave faltando: {missing_keywords}")
                raise Exception(f"Query deve conter: {', '.join(missing_keywords)}")

            # Ajusta aliases se necessário
            if ' FROM PROFISSIONAIS ' in query_upper and ' FROM PROFISSIONAIS P' not in query_upper:
                query = query.replace('FROM profissionais ', 'FROM profissionais p ')

            return query

        except Exception as e:
            print(f"Erro ao gerar query: {e}")
            print("Prompt original:", prompt)
            return None
