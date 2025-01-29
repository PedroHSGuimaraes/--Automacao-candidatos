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


            content = content.replace("```json", "").replace("```", "").strip()


            try:
                dados = json.loads(content)
            except json.JSONDecodeError:
                print("Erro ao fazer parse do JSON")
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
                'nome': str(dados.get('profissao', {}).get('nome', 'profissional')),
                'descricao': str(dados.get('profissao', {}).get('descricao', ''))
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
           
            **8.SUPER IMPORTANTE PROFISSOES SIMILARES:
            -sempre salvar as profissoes segundo para nao repedir {profissoes_classes}
            -sempre salvar as areas de interesse e atuacao para nao repedir {profissoes_classes}
            -sempre salvar as areas de atuação para nao repedir {profissoes_classes}
            
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
            lista_profissoes = []
            # Cria uma lista de todas as profissões e similares para busca
            for profissao, similares in profissoes_classes.items():
                lista_profissoes.append(profissao)
                lista_profissoes.extend(similares)

            profissoes_sql = "'" + "','".join(lista_profissoes) + "'"

            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": f"""Você é um gerador de queries SQL simples e direto.
                        RETORNE APENAS A QUERY, sem explicações ou marcações.

                        Estrutura base da query que você DEVE seguir:
                        SELECT DISTINCT
                            p.nome,
                            p.email,
                            prof.nome as profissao,
                            paa.anos_experiencia,
                            paa.ultimo_cargo,
                            paa.ultima_empresa,
                            aa.nome as area_atuacao,
                            p.habilidades
                        FROM profissionais p
                        LEFT JOIN profissoes prof ON p.profissao_id = prof.id
                        LEFT JOIN profissionais_areas_atuacao paa ON p.id = paa.profissional_id
                        LEFT JOIN areas_atuacao aa ON paa.area_atuacao_id = aa.id
                        WHERE ...

                        Profissões válidas: {profissoes_sql}
                        """
                    },
                    {
                        "role": "user",
                        "content": f"""
                        Crie uma query SQL para: {prompt}

                        REGRAS OBRIGATÓRIAS:
                        1. Use EXATAMENTE a estrutura base fornecida
                        2. Adicione apenas a condição WHERE necessária
                        3. Use sempre LOWER() nas comparações de texto
                        4. Procure sempre em:
                           - prof.nome
                           - paa.ultimo_cargo
                           - paa.descricao_atividades
                           - aa.nome
                           - JSON_CONTAINS(p.habilidades)
                        5. NÃO use ```sql``` ou qualquer outra marcação
                        """
                    }
                ],
                temperature=0.1,
                max_tokens=1000
            )

            query = response.choices[0].message.content.strip()
            query = query.replace('```sql', '').replace('```', '').strip()

            # Validações básicas
            query_upper = query.upper()
            if not query_upper.startswith('SELECT DISTINCT'):
                raise Exception("Query deve começar com SELECT DISTINCT")

            if 'FROM PROFISSIONAIS P' not in query_upper:
                raise Exception("Query deve usar a estrutura base fornecida")

            if 'WHERE' not in query_upper:
                raise Exception("Query deve conter cláusula WHERE")

            return query

        except Exception as e:
            print(f"Erro ao gerar query: {e}")
            print("Prompt original:", prompt)
            # Retorna uma query padrão de segurança
            return """
            SELECT DISTINCT
                p.nome,
                p.email,
                prof.nome as profissao,
                paa.anos_experiencia,
                paa.ultimo_cargo,
                paa.ultima_empresa,
                aa.nome as area_atuacao,
                p.habilidades
            FROM profissionais p
            LEFT JOIN profissoes prof ON p.profissao_id = prof.id
            LEFT JOIN profissionais_areas_atuacao paa ON p.id = paa.profissional_id
            LEFT JOIN areas_atuacao aa ON paa.area_atuacao_id = aa.id
            WHERE LOWER(prof.nome) LIKE LOWER(%s)
            """