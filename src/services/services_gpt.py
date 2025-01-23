# services_gpt.py
import openai
import json
from src.config.config_settings import OPENAI_KEY

class GPTService:
   def __init__(self):
       openai.api_key = OPENAI_KEY

   def analisar_curriculo(self, texto):
       try:
           response = openai.chat.completions.create(
               model="gpt-4",
               messages=[
                   {"role": "system", "content": "Extraia informações estruturadas do currículo."},
                   {"role": "user", "content": f"""
                   Analise este currículo e retorne APENAS um JSON válido com a seguinte estrutura:
                   {{
                       "dados_basicos": {{"nome": "", "email": "", "genero": "", "idade": null}},
                       "formacao": {{"instituto": "", "curso": "", "periodo": ""}},
                       "experiencia": {{"tempo_total": 0, "area_atuacao": "", "ultima_exp": "", "todas_exp": []}},
                       "habilidades": [],
                       "contato": {{"linkedin": "", "github": "", "telefone": ""}},
                       "observacoes": []
                   }}
                   
                   Currículo: {texto}
                   """}
               ]
           )
           
           content = response.choices[0].message.content.strip()
           print(f"GPT Response: {content}")
           return json.loads(content)
           
       except json.JSONDecodeError as e:
           print(f"JSON Error: {e}")
           return self._get_empty_structure()
       except Exception as e:
           print(f"General Error: {e}")
           return self._get_empty_structure()

   def _get_empty_structure(self):
       return {
           "dados_basicos": {"nome": "", "email": "", "genero": "", "idade": None},
           "formacao": {"instituto": "", "curso": "", "periodo": ""},
           "experiencia": {"tempo_total": 0, "area_atuacao": "", "ultima_exp": "", "todas_exp": []},
           "habilidades": [],
           "contato": {"linkedin": "", "github": "", "telefone": ""},
           "observacoes": []
       }

   def gerar_query_sql(self, prompt, schema):
       try:
           response = openai.chat.completions.create(
               model="gpt-4",
               messages=[
                   {"role": "system", "content": "Gere queries SQL válidas para MySQL."},
                   {"role": "user", "content": f"""
                   Schema do banco:
                   {schema}
                   
                   Gere uma query SQL para responder:
                   {prompt}
                   
                   Retorne APENAS a query SQL, sem explicações.
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
               model="gpt-4",
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
           return response.choices[0].message.content
       except Exception as e:
           print(f"Response Error: {e}")
           return "Erro ao processar resposta."