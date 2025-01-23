# src/services/pdf_service.py
import PyPDF2

class PDFService:
    @staticmethod
    def extrair_texto(arquivo_pdf):
        try:
            pdf_reader = PyPDF2.PdfReader(arquivo_pdf)
            texto = ""
            for pagina in pdf_reader.pages:
                texto += pagina.extract_text()
            return texto
        except Exception as e:
            raise Exception(f"Erro ao ler PDF: {e}")