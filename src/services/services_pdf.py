from pdfminer.high_level import extract_text
from pdfminer.layout import LAParams, LTTextBox, LTText, LTChar
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from io import StringIO, BytesIO
import re
from typing import List, Dict, Tuple, Set
import logging


class PDFService:
    def __init__(self):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        self.resource_manager = PDFResourceManager()
        self.laparams = LAParams(
            line_margin=0.5,
            word_margin=0.1,
            char_margin=2.0,
            boxes_flow=0.5,
            detect_vertical=True,
            all_texts=True
        )

        # Padrões que identificam início de um novo currículo
        self.inicio_patterns = [
            r'curr[ií]culo\s*v[ií]tae',
            r'^dados\s*pessoais',
            r'^informa[çc][õo]es\s*pessoais',
            r'^objetivo\s*profissional',
            r'^nome\s*completo?\s*:',
            r'^nome\s*:',
            r'^\s*(?:candidato|candidata)\s*:'
        ]

        # Padrões que identificam seções comuns de currículos
        self.secao_patterns = [
            r'^experi[êe]ncia\s*profissional',
            r'^forma[çc][ãa]o\s*acad[êe]mica',
            r'^qualifica[çc][õo]es',
            r'^habilidades',
            r'^idiomas',
            r'^cursos',
            r'^certifica[çc][õo]es'
        ]

        # Padrões que indicam final de currículo
        self.fim_patterns = [
            r'refer[êe]ncias\s*profissionais?\s*$',
            r'disponibilidade\s*(?:para|de)\s*(?:início|começo)',
            r'pret[êe]ns[ãa]o\s*salarial',
            r'-{3,}|_{3,}|\*{3,}',  # Linhas separadoras
            r'\f(?!\s*(?:experi[êe]ncia|forma[çc][ãa]o|curso))'  # Quebra de página não seguida de seção comum
        ]

    def _extrair_texto_pagina(self, pagina) -> str:
        """Extrai texto de uma única página mantendo a formatação"""
        device = PDFPageAggregator(self.resource_manager, laparams=self.laparams)
        interpreter = PDFPageInterpreter(self.resource_manager, device)
        interpreter.process_page(pagina)
        layout = device.get_result()

        # Ordena elementos por posição (top para bottom, left para right)
        elementos = []
        for elemento in layout:
            if isinstance(elemento, LTTextBox):
                elementos.append((
                    -elemento.y0,  # Negativo para ordenar top->bottom
                    elemento.x0,
                    elemento.get_text()
                ))

        elementos.sort()  # Ordena por posição
        return '\n'.join(texto for _, _, texto in elementos)

    def _e_inicio_curriculo(self, texto: str) -> bool:
        """Verifica se o texto indica início de um novo currículo"""
        texto_inicio = texto[:500].lower()

        # Verifica padrões de início
        for pattern in self.inicio_patterns:
            if re.search(pattern, texto_inicio, re.IGNORECASE | re.MULTILINE):
                return True

        # Verifica se tem um nome seguido de informações de contato
        if (re.search(r'^[A-ZÀ-Ú][a-zà-ú]{2,}\s+[A-ZÀ-Ú][a-zà-ú\s]{2,}', texto_inicio) and
                (re.search(r'[\w\.-]+@[\w\.-]+\.\w+', texto_inicio) or  # email
                 re.search(r'\(\d{2}\)\s*\d{4,5}-?\d{4}', texto_inicio))):  # telefone
            return True

        return False

    def _e_continuacao_curriculo(self, texto_anterior: str, texto_atual: str) -> bool:
        """Verifica se o texto atual é continuação do currículo anterior"""
        # Se começa com uma seção comum de currículo
        for pattern in self.secao_patterns:
            if re.match(pattern, texto_atual.lstrip(), re.IGNORECASE):
                return True

        # Se o texto anterior termina no meio de uma frase ou seção
        if texto_anterior.rstrip()[-1] not in {'.', '!', '?', ':'}:
            return True

        # Se não tem indicadores de novo currículo
        return not self._e_inicio_curriculo(texto_atual)

    def _e_fim_curriculo(self, texto: str) -> bool:
        """Verifica se o texto indica fim de um currículo"""
        for pattern in self.fim_patterns:
            if re.search(pattern, texto, re.IGNORECASE | re.MULTILINE):
                return True
        return False

    def extrair_curriculos_multiplos(self, arquivo_pdf) -> List[Tuple[Dict[str, str], str]]:
        """Extrai múltiplos currículos de um PDF mantendo a continuidade entre páginas"""
        try:
            if not isinstance(arquivo_pdf, BytesIO):
                pdf_bytes = BytesIO(arquivo_pdf.read())
            else:
                pdf_bytes = arquivo_pdf
                pdf_bytes.seek(0)

            # Lista para armazenar currículos extraídos
            curriculos = []
            curriculo_atual = []
            info_atual = {}

            # Processa cada página
            paginas = list(PDFPage.get_pages(pdf_bytes))
            for i, pagina in enumerate(paginas):
                texto_pagina = self._extrair_texto_pagina(pagina)

                # Se é a primeira página ou início claro de novo currículo
                if i == 0 or self._e_inicio_curriculo(texto_pagina):
                    # Se já tem currículo em processamento, salva ele
                    if curriculo_atual:
                        texto_completo = '\n'.join(curriculo_atual)
                        if self.validar_curriculo(texto_completo):
                            info = self._extrair_info_candidato(texto_completo)
                            if any(info.values()):  # Se encontrou alguma informação
                                curriculos.append((info, texto_completo))

                    # Inicia novo currículo
                    curriculo_atual = [texto_pagina]
                    info_atual = self._extrair_info_candidato(texto_pagina)

                # Se é continuação do currículo atual
                elif self._e_continuacao_curriculo('\n'.join(curriculo_atual), texto_pagina):
                    curriculo_atual.append(texto_pagina)

                    # Atualiza informações se encontrar dados adicionais
                    info_pagina = self._extrair_info_candidato(texto_pagina)
                    for key, value in info_pagina.items():
                        if value and not info_atual.get(key):
                            info_atual[key] = value

                # Se não é continuação clara, verifica o contexto
                else:
                    # Divide o texto em seções
                    secoes = re.split(r'\n\s*\n', texto_pagina)
                    for secao in secoes:
                        if self._e_inicio_curriculo(secao):
                            # Salva currículo anterior
                            if curriculo_atual:
                                texto_completo = '\n'.join(curriculo_atual)
                                if self.validar_curriculo(texto_completo):
                                    curriculos.append((info_atual, texto_completo))

                            # Inicia novo currículo
                            curriculo_atual = [secao]
                            info_atual = self._extrair_info_candidato(secao)
                        else:
                            curriculo_atual.append(secao)

            # Processa o último currículo
            if curriculo_atual:
                texto_completo = '\n'.join(curriculo_atual)
                if self.validar_curriculo(texto_completo):
                    if not info_atual:
                        info_atual = self._extrair_info_candidato(texto_completo)
                    if any(info_atual.values()):
                        curriculos.append((info_atual, texto_completo))

            return curriculos

        except Exception as e:
            self.logger.error(f"Erro ao processar PDF: {str(e)}")
            raise Exception(f"Erro ao processar PDF: {str(e)}")

    def _extrair_info_candidato(self, texto: str) -> Dict[str, str]:
        """Extrai informações básicas do candidato do texto"""
        info = {
            'nome': self._encontrar_nome(texto),
            'email': self._encontrar_email(texto),
            'telefone': self._encontrar_telefone(texto)
        }
        return info

    def _encontrar_nome(self, texto: str) -> str:
        """Encontra o nome do candidato no texto"""
        padroes_nome = [
            r'nome:?\s*([A-ZÀ-Ú][A-zÀ-ú\s]{2,}?)(?=\n|\r|$)',
            r'^([A-ZÀ-Ú][A-zÀ-ú\s]{2,}?)(?=\n|\r|$)',
            r'curr[ií]culo\s*v[ií]tae\s*[-:]?\s*([A-ZÀ-Ú][A-zÀ-ú\s]{2,}?)(?=\n|\r|$)'
        ]

        for padrao in padroes_nome:
            try:
                match = re.search(padrao, texto, re.IGNORECASE | re.MULTILINE)
                if match and match.groups():
                    nome = match.group(1).strip()
                    if len(nome.split()) >= 2:
                        return nome
            except:
                continue
        return ""

    def _encontrar_email(self, texto: str) -> str:
        """Encontra o email no texto"""
        try:
            padrao_email = r'[\w\.-]+@[\w\.-]+\.\w+'
            match = re.search(padrao_email, texto)
            return match.group(0) if match else ""
        except:
            return ""

    def _encontrar_telefone(self, texto: str) -> str:
        """Encontra o telefone no texto"""
        try:
            padrao_telefone = r'(?:(?:\+?55\s?)?(?:\(?\d{2}\)?[\s-]?)?)(?:\d{4,5}[-\s]?\d{4})'
            match = re.search(padrao_telefone, texto)
            return match.group(0) if match else ""
        except:
            return ""

    def validar_curriculo(self, texto: str) -> bool:
        """Valida se o texto parece ser um currículo válido"""
        if not texto or len(texto.strip()) < 100:
            return False

        palavras_chave = [
            'experiência', 'formação', 'educação', 'profissional',
            'objetivo', 'habilidades', 'competências', 'conhecimentos',
            'telefone', 'email', 'endereço', 'graduação', 'curso'
        ]

        texto_lower = texto.lower()
        palavras_encontradas = sum(1 for palavra in palavras_chave if palavra in texto_lower)

        # Critérios mínimos
        tem_nome = bool(self._encontrar_nome(texto))
        tem_contato = bool(self._encontrar_email(texto) or self._encontrar_telefone(texto))
        tem_palavras_chave = palavras_encontradas >= 3

        return tem_nome or (tem_contato and tem_palavras_chave)