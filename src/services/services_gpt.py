import openai
import json
import re
from src.config.config_settings import OPENAI_KEY


class GPTService:
    def __init__(self):
        openai.api_key = OPENAI_KEY
        self.system_message = {
            "role": "system",
            "content": """
            Você é um analisador de currículos especializado na extração e estruturação de dados. 
            **Extraia e preencha corretamente todos os campos especificados**, atribuindo os dados às colunas correspondentes no banco de dados.

            **IMPORTANTE SOBRE ÁREAS:**
            - Ao identificar áreas de interesse e atuação, SEMPRE consulte a lista de áreas existentes fornecida
            - Use preferencialmente áreas já cadastradas para manter consistência
            - Se encontrar uma área nova, ela deve ser MUITO similar às existentes
            - Separe claramente áreas de interesse (aspirações) das áreas de atuação (experiência real)

            **REGRAS GERAIS:**
            - Caso alguma informação relevante não tenha uma coluna correspondente, **salve-a na coluna `campos_dinamicos`** com uma chave descritiva
            - Sempre retorne **todas** as colunas esperadas, mesmo que vazias (use "" ou null)
            - Converta **todos os valores textuais para lowercase**
            - Utilize **sinônimos e variações** para garantir a extração correta
            - **NÃO OMITA** campos e valores que possam ser derivados do conteúdo analisado
            - NÃO INCLUA ```json NA RESPOSTA
            """
        }

    def _validate_and_fix_json(self, content):
        """Valida e corrige problemas comuns no JSON"""
        try:
            # Remove caracteres especiais e quebras de linha indesejadas
            content = re.sub(r'[\n\r\t]', ' ', content)

            # Tenta encontrar o JSON válido dentro do texto
            json_match = re.search(r'\{[\s\S]*\}', content)
            if not json_match:
                return self._get_empty_structure()

            json_str = json_match.group()

            # Tenta fazer o parse do JSON
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                # Se falhar, tenta limpar e corrigir o JSON
                json_str = re.sub(r',\s*}', '}', json_str)  # Remove vírgulas extras
                json_str = re.sub(r',\s*]', ']', json_str)  # Remove vírgulas extras em arrays
                json_str = re.sub(r'"}[\s\n]*,[\s\n]*"', '", "', json_str)  # Corrige formatação
                return json.loads(json_str)

        except Exception as e:
            print(f"Erro ao processar JSON: {e}")
            print("Content recebido:", content)
            return self._get_empty_structure()

    def analisar_curriculo(self, texto):
        try:
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[self.system_message, self.user_message(texto)],
                temperature=0.1
            )
            content = response.choices[0].message.content.strip()

            # Valida e corrige o JSON antes de retornar
            dados = self._validate_and_fix_json(content)

            # Garante que todos os campos obrigatórios existem
            dados = self._ensure_required_fields(dados)

            return dados

        except Exception as e:
            print(f"Erro: {e}")
            print("Resposta:", content if 'content' in locals() else 'N/A')
            return self._get_empty_structure()

    def _ensure_required_fields(self, dados):
        """Garante que todos os campos obrigatórios existem"""
        template = self._get_empty_structure()

        if not isinstance(dados, dict):
            return template


        def merge_dicts(template, data):
            if not isinstance(data, dict):
                return data
            result = template.copy()[0]
            for key, value in data.items():
                if key in template and isinstance(template[key], dict):
                    result[key] = merge_dicts(template[key], value)
                else:
                    result[key] = value
            return result

        return merge_dicts(template, dados)


    def user_message(self, texto, areas_existentes=None):
        areas_contexto = ""
        if areas_existentes:
            areas_contexto = f"""
                **AREAS JA CADASTRADAS NO SISTEMA:**
                - Areas de Interesse: {[area['nome'] for area in areas_existentes.get('interesse', [])]}
                - Areas de Atuacao: {[area['nome'] for area in areas_existentes.get('atuacao', [])]}

                **IMPORTANTE:** Utilize preferencialmente estas areas existentes!
                """

        return {
            "role": "user",
            "content": f"""
                **Schema do banco de dados:**
                ```
                id INT AUTO_INCREMENT PRIMARY KEY,
                nome VARCHAR(255),
                email VARCHAR(255),
                genero VARCHAR(50),
                idade INT,
                instituto_formacao VARCHAR(255),
                curso VARCHAR(255),
                periodo VARCHAR(50),
                tempo_experiencia FLOAT,
                ultima_experiencia TEXT,
                todas_experiencias TEXT,
                habilidades TEXT,
                linkedin VARCHAR(255),
                github VARCHAR(255),
                telefone VARCHAR(50),
                data_criacao DATETIME,
                pdf_conteudo LONGTEXT,
                observacoes_ia TEXT,
                campos_dinamicos TEXT,
                areas_interesse TEXT,
                areas_atuacao TEXT
                ```

                **Resumo do banco de dados (db_summary):**
                - **id:** identificador unico autoincremental
                - **nome:** nome completo do candidato em lowercase (ex: "joao silva")
                - **email:** email de contato do candidato (ex: "joao@email.com")
                - **genero:** masculino/feminino/nao identificado, baseado no nome se nao especificado (ex: "masculino")
                - **idade:** idade numerica do candidato (ex: 25)
                - **instituto_formacao:** nome da instituicao de ensino em lowercase (ex: "ufmg")
                - **curso:** nome do curso em lowercase (ex: "engenharia de computacao")
                - **periodo:** periodo atual ou status do curso em lowercase (ex: "5o periodo" ou "concluido")
                - **tempo_experiencia:** anos de experiencia profissional como decimal (ex: 2.5)
                - **ultima_experiencia:** descricao da experiencia mais recente em lowercase
                - **todas_experiencias:** array JSON com historico de experiencias em lowercase
                - **habilidades:** array JSON com lista de habilidades tecnicas em lowercase
                - **linkedin:** URL completa do perfil do LinkedIn
                - **github:** URL completa do perfil do GitHub
                - **telefone:** numero de telefone com DDD e pais (ex: "+5531999999999")
                - **data_criacao:** data e hora do cadastro (automatico)
                - **pdf_conteudo:** conteudo completo do PDF em lowercase
                - **observacoes_ia:** array JSON com observacoes relevantes em lowercase
                - **campos_dinamicos:** objeto JSON com informacoes extras em lowercase
                - **areas_interesse:** array JSON com areas de interesse profissional em lowercase
                - **areas_atuacao:** array JSON com areas de experiencia comprovada em lowercase

                {areas_contexto}

                **Instrucoes para analise do curriculo:**
                1. Extraia todas as informacoes do curriculo abaixo e retorne APENAS JSON com a estrutura exata:
                ```json
                {{
                    "dados_basicos": {{
                        "nome": "string",
                        "email": "string",
                        "genero": "string",
                        "idade": number
                    }},
                    "formacao": {{
                        "instituto_formacao": "string",
                        "curso": "string",
                        "periodo": "string"
                    }},
                    "experiencia": {{
                        "tempo_experiencia": number,
                        "areas_interesse": ["string"],
                        "areas_atuacao": ["string"],
                        "ultima_experiencia": "string",
                        "todas_experiencias": ["string"]
                    }},
                    "habilidades": ["string"],
                    "contato": {{
                        "linkedin": "string",
                        "github": "string",
                        "telefone": "string"
                    }},
                    "observacoes_ia": ["string"],
                    "campos_dinamicos": {{"chave": "valor"}}
                }}
                ```

                2. **IMPORTANTE - Use EXATAMENTE estas chaves:**
                   - instituto_formacao (nao use "instituto")
                   - tempo_experiencia (nao use "tempo_total")
                   - ultima_experiencia (nao use "ultima_exp")
                   - todas_experiencias (nao use "todas_exp")
                   - observacoes_ia (nao use "observacoes")
                   - areas_interesse e areas_atuacao como arrays

                3. **Nao deixe nenhum campo em branco no JSON.** Use "" ou [] para campos vazios.

                4. **Todo texto deve ser convertido para lowercase** para garantir consistencia.

                5. Se uma informacao relevante for encontrada e nao houver uma coluna correspondente, 
                   salve-a dentro de `campos_dinamicos` no formato chave-valor.

                **Curriculo para analise:** 
                {texto}
                """
        }

    def analisar_curriculo(self, texto):
        try:
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[self.system_message, self.user_message(texto)],
                temperature=0.1
            )
            content = response.choices[0].message.content.strip()


            content = content.replace("```json", "").replace("```", "").strip()


            try:
                return json.loads(content)
            except json.JSONDecodeError:

                json_match = re.search(r"\{[\s\S]*\}", content)
                if (json_match):
                    return json.loads(json_match.group())
                raise

        except Exception as e:
            print(f"Erro: {e}\nResposta: {content if 'content' in locals() else 'N/A'}")
            return self._get_empty_structure()

    def gerar_query_sql(self, prompt, schema):
        try:
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Gere queries MySQL válidas e otimizadas para MySQL."},
                    {"role": "user", "content": f"""
                    Schema do banco de dados:
                    {schema}

                    **Resumo do banco de dados (db_summary):**
                    - **Tabela:** [nome_da_tabela]
                    - **coluna1 (tipo)**: [exemplo de valor], [exemplo de valor]
                    - **coluna2 (tipo)**: [exemplo de valor], [exemplo de valor]
                    - **coluna3 (tipo)**: [exemplo de valor], [exemplo de valor]

                    **Instruções:**
                    1. Gere uma query MySQL válida e otimizada para a seguinte necessidade:
                    **{prompt}**
                    2. Sempre retorne **apenas** a query MySQL, sem explicações adicionais.
                    3. Nunca utilize ```sql```, apenas o comando puro.
                    4. Para colunas do tipo `string`, sempre trate os valores em **lowercase**, garantindo consistência nos resultados.
                    5. Utilize sinônimos ou variações para buscas em colunas `string`, ampliando a precisão da consulta.
                    6. Evite consultas complexas desnecessárias e utilize índices quando possível para melhorar a performance.

                    Gere a consulta conforme as diretrizes acima.
                    """}
                ]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Query Error: {e}")
            return None

    def processar_resposta(self, prompt, dados):
        try:
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Analise dados e responda perguntas."},
                    {"role": "user", "content": f"""
                    Dados disponíveis:
                    {json.dumps(dados, indent=2)}

                    Pergunta:
                    {prompt}
                    """}
                ]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Response Error: {e}")
            return "Erro ao processar resposta."


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