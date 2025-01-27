from pdfminer.high_level import extract_text

class PDFService:
    @staticmethod
    def extrair_texto(arquivo_pdf):
        try:
            texto = extract_text(arquivo_pdf)
            if not texto.strip():
                raise ValueError("Nenhum texto extraído do PDF. Verifique se o arquivo contém texto reconhecível.")
            return texto
        except Exception as e:
            raise Exception(f"Erro ao ler PDF: {e}")
