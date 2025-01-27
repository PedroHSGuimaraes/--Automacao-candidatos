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
           Caso alguma informação relevante não tenha uma coluna correspondente, **salve-a na coluna `campos_dinamicos`** com uma chave descritiva. 
           - Sempre retorne **todas** as colunas esperadas, mesmo que vazias (use "" ou null).
           - Converta **todos os valores textuais para lowercase**.
           - Utilize **sinônimos e variações** para garantir a extração correta.
           - **NÃO OMITA** campos e valores que possam ser derivados do conteúdo analisado.
           -NÃO INCLUA  ```json NA RESPOSTA
           """
       }

   def user_message(self, texto):
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
           area_atuacao VARCHAR(255),
           ultima_experiencia TEXT,
           todas_experiencias TEXT,
           habilidades TEXT,
           linkedin VARCHAR(255),
           github VARCHAR(255),
           telefone VARCHAR(50),
           data_criacao DATETIME,
           pdf_conteudo LONGTEXT,
           observacoes_ia JSON,
           campos_dinamicos JSON
           ```

           **Resumo do banco de dados (db_summary):**
           - **nome (VARCHAR):** nome completo do candidato, ex: "joão silva" (sempre lowercase).
           - **email (VARCHAR):** e-mail do candidato, ex: "joao@email.com".
           - **genero (VARCHAR):** gênero do candidato, ex: "masculino", "feminino" se nao tiver no curriculo julgue com base no nome Exemplo : João Silva → masculino, Maria Souza → feminino, Alex Lima → não identificado.:(sempre lowercase).
           - **idade (INT):** idade do candidato, ex: 25, 30.
           - **instituto_formacao (VARCHAR):** instituição de ensino, ex: "ufmg" (sempre lowercase).
           - **curso (VARCHAR):** curso realizado, ex: "engenharia" (sempre lowercase).
           - **periodo (VARCHAR):** período acadêmico do curso ou se ja concluiu, ex: "4º Período - Formatura Dez/26 ou em adantamento ou concluído , etc" (sempre lowercase).
           - **tempo_experiencia (FLOAT):** anos de experiência, ex: 2.5, 5.0.
           - **area_atuacao (VARCHAR):** área profissional, ex: "tecnologia" (sempre lowercase).
           - **ultima_experiencia (TEXT):** resumo da última experiência profissional (sempre lowercase).
           e).
           - **habilidades (TEXT):** habilidades técnicas, ex: "python, sql"(sempre lowercase).
           - **linkedin (VARCHAR):** URL do LinkedIn do candidato.
           - **github (VARCHAR):** URL do GitHub do candidato.
           - **telefone (VARCHAR):** telefone do candidato, ex: "+5511999999999".
           - **pdf_conteudo (LONGTEXT):** conteúdo extraído do PDF (sempre lowercase).
           - **observacoes_ia (JSON):** faça um resumo de todas as informações extraídas (sempre lowercase).
           - **campos_dinamicos (JSON):** informações adicionais não mapeadas (sempre lowercase).

           **Instruções para análise do currículo:**
           1. Extraia todas as informações do currículo abaixo e retorne APENAS JSON com a estrutura exata:
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
                   "area_atuacao": "string",
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
               "campos_dinamicos": {{"informacao_extra": "string"}}
           }}
           ```

           2. **Não deixe nenhum campo em branco no JSON.** Caso a informação não esteja presente, preencha com "" (string vazia) ou null.

           3. **Todo texto deve ser convertido para lowercase** para garantir consistência.

           4. Se uma informação relevante for encontrada e não houver uma coluna correspondente, salve-a dentro de `campos_dinamicos` no formato chave-valor.

           **Currículo para análise:** 
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
           
           # Remove markdown e limpa o texto
           content = content.replace("```json", "").replace("```", "").strip()
           
           # Tenta extrair JSON válido
           try:
               return json.loads(content)
           except json.JSONDecodeError:
               # Se falhar, tenta extrair usando regex
               json_match = re.search(r"\{[\s\S]*\}", content)
               if json_match:
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
           "dados_basicos": {"nome": "", "email": "", "genero": "", "idade": None},
           "formacao": {"instituto": "", "curso": "", "periodo": ""},
           "experiencia": {"tempo_total": 0, "area_atuacao": "", "ultima_exp": "", "todas_exp": []},
           "habilidades": [],
           "contato": {"linkedin": "", "github": "", "telefone": ""},
           "observacoes": []
       }