import json
from datetime import datetime
from src.database.database_connection import DatabaseConnection
from src.utils.classes_profissao import profissoes_classes

class DataService:
    def __init__(self):
        self.conn = None
        self.cursor = None

    def _get_connection(self):
        self.conn, self.cursor = DatabaseConnection.get_connection()

    def _close_connection(self):
        DatabaseConnection.close_connection(self.conn, self.cursor)

    def _converter_estado_para_sigla(self, estado):
        """
        Converte o nome do estado para sua sigla
        """
        if not estado:
            return ''

        estado = estado.lower().strip()

        # Se já é uma sigla válida
        if estado.upper() in self.estados.values():
            return estado.upper()

        # Se é um nome de estado
        return self.estados.get(estado, '')

    def _get_or_create_genero(self, genero_data):
        """
        Busca ou cria um gênero no banco de dados
        """
        try:
            # Trata o caso em que genero_data é uma string
            if isinstance(genero_data, str):
                nome = genero_data.lower().strip()
                descricao = ""
            else:
                # Trata o caso em que genero_data é um dicionário
                nome = genero_data.get('nome', 'não identificado').lower().strip()
                descricao = genero_data.get('descricao', '').lower().strip()

            # Validar se é um dos valores permitidos
            if nome not in ['masculino', 'feminino', 'não identificado']:
                nome = 'não identificado'

            # Buscar gênero existente
            self.cursor.execute(
                "SELECT id FROM generos WHERE LOWER(nome) = %s",
                (nome,)
            )
            resultado = self.cursor.fetchone()

            if resultado:
                genero_id = resultado['id']
                # Atualiza descrição se fornecida
                if descricao:
                    self.cursor.execute(
                        "UPDATE generos SET descricao = %s WHERE id = %s",
                        (descricao, genero_id)
                    )
                return genero_id

            # Se não existe, cria novo
            self.cursor.execute(
                "INSERT INTO generos (nome, descricao) VALUES (%s, %s)",
                (nome, descricao)
            )
            return self.cursor.lastrowid

        except Exception as e:
            print(f"Erro ao buscar/criar gênero: {e}")
            # Retorna ID do gênero 'não identificado'
            self.cursor.execute(
                "SELECT id FROM generos WHERE nome = 'não identificado'"
            )
            return self.cursor.fetchone()['id']

    def salvar_profissional(self, dados, texto_pdf):
        """
        Salva um profissional e seus relacionamentos no banco de dados
        """
        try:
            self._get_connection()

            # 1. Salvar ou obter profissão
            profissao_id = self._get_or_create_profissao(dados['profissao']['nome'])

            # 2. Salvar ou obter faculdade
            faculdade_id = self._get_or_create_faculdade(
                dados['faculdade']['nome'],
                dados['faculdade']['cidade'],
                dados['faculdade']['estado']
            )

            # 3. Salvar ou obter gênero
            genero_id = self._get_or_create_genero(dados['profissional']['genero'])

            # 4. Identificar idioma principal
            idioma_principal_id = None
            nivel_idioma_principal = None
            if dados['idiomas']:
                # Procura primeiro por inglês
                idioma_principal = next(
                    (idioma for idioma in dados['idiomas'] if 'ingles' in idioma['nome'].lower()),
                    dados['idiomas'][0]  # Se não encontrar inglês, usa o primeiro da lista
                )

                # Busca ou cria o idioma principal
                idioma_principal_id = self._get_or_create_idioma(idioma_principal['nome'])
                nivel_idioma_principal = idioma_principal.get('nivel', '').lower()

            # 5. Inserir profissional
            query = """
               INSERT INTO profissionais (
                   nome, email, telefone, endereco, portfolio_url, linkedin_url,
                   github_url, profissao_id, faculdade_id, genero_id, pdf_curriculo,
                   idade, pretensao_salarial, disponibilidade, tipo_contrato,
                   observacoes_ia, campos_dinamicos, idioma_principal_id, nivel_idioma_principal
               ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               """

            valores = (
                dados['profissional']['nome'],
                dados['profissional']['email'],
                dados['profissional']['telefone'],
                dados['profissional']['endereco'],
                dados['profissional']['portfolio_url'],
                dados['profissional']['linkedin_url'],
                dados['profissional']['github_url'],
                profissao_id,
                faculdade_id,
                genero_id,
                texto_pdf,
                dados['profissional']['idade'],
                dados['profissional']['pretensao_salarial'],
                dados['profissional']['disponibilidade'],
                dados['profissional']['tipo_contrato'],
                json.dumps(dados['profissional']['observacoes_ia']),
                json.dumps(dados['profissional']['campos_dinamicos']),
                idioma_principal_id,
                nivel_idioma_principal
            )
            self.cursor.execute(query, valores)
            profissional_id = self.cursor.lastrowid

            # 6. Salvar todos os idiomas
            for idioma in dados['idiomas']:
                self._salvar_idioma(profissional_id, idioma)

            # 7. Salvar áreas de interesse
            for area in dados['areas_interesse']:
                self._salvar_area_interesse(profissional_id, area)

            # 8. Salvar áreas de atuação
            for area in dados['areas_atuacao']:
                self._salvar_area_atuacao(profissional_id, area)

            self.conn.commit()
            return profissional_id

        except Exception as e:
            if self.conn:
                self.conn.rollback()
            raise Exception(f"Erro ao salvar profissional: {e}")

        finally:
            self._close_connection()

    def _get_or_create_profissao(self, nome):
        """Busca ou cria uma profissão considerando similaridade"""
        nome = nome.lower().strip()

        # Dicionário de profissões similares
        profissoes_similares = profissoes_classes

        # Verifica se o nome está nas chaves do dicionário de similaridade
        if nome in profissoes_similares:
            nome_padrao = nome
        else:
            # Busca o nome padrão para o qual o nome fornecido é similar
            for profissao, similares in profissoes_similares.items():
                if nome in similares:
                    nome_padrao = profissao
                    break
            else:
                nome_padrao = nome

        # Busca profissão existente pelo nome padrão
        self.cursor.execute(
            "SELECT id FROM profissoes WHERE LOWER(nome) = %s",
            (nome_padrao,)
        )
        result = self.cursor.fetchone()

        if result:
            return result['id']

        # Cria nova profissão com o nome padrão
        self.cursor.execute(
            "INSERT INTO profissoes (nome) VALUES (%s)",
            (nome_padrao,)
        )
        return self.cursor.lastrowid
    def _get_or_create_faculdade(self, nome, cidade='', estado=''):
        """Busca ou cria uma faculdade"""
        nome = nome.lower().strip()

        # Busca faculdade existente
        self.cursor.execute(
            "SELECT id FROM faculdades WHERE LOWER(nome) = %s",
            (nome,)
        )
        result = self.cursor.fetchone()

        if result:
            return result['id']

        # Cria nova faculdade
        self.cursor.execute(
            "INSERT INTO faculdades (nome, cidade, estado) VALUES (%s, %s, %s)",
            (nome, cidade.lower(), estado.lower())
        )
        return self.cursor.lastrowid

    def _get_or_create_idioma(self, nome):
        """
        Busca ou cria um idioma, evitando duplicatas
        """
        try:
            nome = nome.lower().strip()

            # Primeiro busca se já existe
            self.cursor.execute(
                "SELECT id FROM idiomas WHERE LOWER(nome) = %s",
                (nome,)
            )
            result = self.cursor.fetchone()

            if result:
                return result['id']

            # Se não existe, cria novo
            self.cursor.execute(
                "INSERT INTO idiomas (nome) VALUES (%s)",
                (nome,)
            )
            return self.cursor.lastrowid

        except Exception as e:
            print(f"Erro ao buscar/criar idioma: {e}")
            raise

    def _salvar_idioma(self, profissional_id, idioma):
        """
        Salva um idioma para o profissional, evitando duplicatas
        """
        try:
            # Primeiro busca se o idioma já existe
            self.cursor.execute(
                "SELECT id FROM idiomas WHERE LOWER(nome) = %s",
                (idioma['nome'].lower(),)
            )
            resultado = self.cursor.fetchone()

            if resultado:
                idioma_id = resultado['id']
            else:
                # Se não existe, cria novo idioma
                self.cursor.execute(
                    "INSERT INTO idiomas (nome, codigo) VALUES (%s, %s)",
                    (idioma['nome'].lower(), idioma.get('codigo', ''))
                )
                idioma_id = self.cursor.lastrowid

            # Agora cria ou atualiza o relacionamento
            self.cursor.execute("""
                INSERT INTO profissionais_idiomas 
                    (profissional_id, idioma_id, nivel, certificacao) 
                VALUES 
                    (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    nivel = VALUES(nivel),
                    certificacao = VALUES(certificacao)
            """, (
                profissional_id,
                idioma_id,
                idioma.get('nivel', '').lower(),
                idioma.get('certificacao', '')
            ))

        except Exception as e:
            print(f"Erro ao salvar idioma: {e}")
            raise

    def _salvar_area_interesse(self, profissional_id, area):
        """
        Salva uma área de interesse para o profissional, considerando similaridade
        """
        try:
            nome = area['nome'].lower().strip()

            # Dicionário de áreas de interesse similares
            areas_interesse_similares = profissoes_classes

            nome_padrao = nome
            for area_interesse, similares in areas_interesse_similares.items():
                if nome in similares:
                    nome_padrao = area_interesse
                    break

            # Busca área existente pelo nome padrão
            self.cursor.execute(
                "SELECT id FROM areas_interesse WHERE LOWER(nome) = %s",
                (nome_padrao,)
            )
            resultado = self.cursor.fetchone()

            if resultado:
                area_id = resultado['id']
            else:
                # Cria nova área com o nome padrão
                self.cursor.execute(
                    "INSERT INTO areas_interesse (nome) VALUES (%s)",
                    (nome_padrao,)
                )
                area_id = self.cursor.lastrowid

            # Cria ou atualiza o relacionamento
            self.cursor.execute("""
                INSERT INTO profissionais_areas_interesse
                    (profissional_id, area_interesse_id, nivel_interesse)
                VALUES
                    (%s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    nivel_interesse = VALUES(nivel_interesse)
            """, (
                profissional_id,
                area_id,
                area.get('nivel_interesse', 3)
            ))

        except Exception as e:
            print(f"Erro ao salvar área de interesse: {e}")
            raise

    def _salvar_area_atuacao(self, profissional_id, area):
        """
        Salva uma área de atuação para o profissional, considerando similaridade
        """
        try:
            nome = area['nome'].lower().strip()

            # Dicionário de áreas de atuação similares
            areas_atuacao_similares = profissoes_classes
            nome_padrao = nome
            for area_padrao, similares in areas_atuacao_similares.items():
                if nome in similares:
                    nome_padrao = area_padrao
                    break

            # Busca área existente pelo nome padrão
            self.cursor.execute(
                "SELECT id FROM areas_atuacao WHERE LOWER(nome) = %s",
                (nome_padrao,)
            )
            resultado = self.cursor.fetchone()

            if resultado:
                area_id = resultado['id']
            else:
                # Cria nova área com o nome padrão
                self.cursor.execute(
                    "INSERT INTO areas_atuacao (nome) VALUES (%s)",
                    (nome_padrao,)
                )
                area_id = self.cursor.lastrowid

            # Cria ou atualiza o relacionamento
            self.cursor.execute("""
                INSERT INTO profissionais_areas_atuacao
                    (profissional_id, area_atuacao_id, anos_experiencia,
                     ultimo_cargo, ultima_empresa, descricao_atividades)
                VALUES 
                    (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    anos_experiencia = VALUES(anos_experiencia),
                    ultimo_cargo = VALUES(ultimo_cargo),
                    ultima_empresa = VALUES(ultima_empresa),
                    descricao_atividades = VALUES(descricao_atividades)  
            """, (
                profissional_id,
                area_id,
                area.get('anos_experiencia', 0),
                area.get('ultimo_cargo', ''),
                area.get('ultima_empresa', ''),
                area.get('descricao_atividades', '')
            ))

        except Exception as e:
            print(f"Erro ao salvar área de atuação: {e}")
            raise
    def buscar_profissionais(self, filtros=None):
        """
        Busca profissionais com filtros opcionais
        """
        try:
            self._get_connection()

            query = """
            SELECT 
                p.*, 
                prof.nome as profissao,
                g.nome as genero,
                f.nome as faculdade,
                i.nome as idioma_principal,
                GROUP_CONCAT(DISTINCT CONCAT(i2.nome, ' (', pi.nivel, ')')) as idiomas,
                GROUP_CONCAT(DISTINCT ai.nome) as areas_interesse,
                GROUP_CONCAT(DISTINCT CONCAT(aa.nome, ' (', paa.anos_experiencia, ' anos)')) as areas_atuacao
            FROM profissionais p
            LEFT JOIN profissoes prof ON p.profissao_id = prof.id
            LEFT JOIN generos g ON p.genero_id = g.id
            LEFT JOIN faculdades f ON p.faculdade_id = f.id
            LEFT JOIN idiomas i ON p.idioma_principal_id = i.id
            LEFT JOIN profissionais_idiomas pi ON p.id = pi.profissional_id
            LEFT JOIN idiomas i2 ON pi.idioma_id = i2.id
            LEFT JOIN profissionais_areas_interesse pai ON p.id = pai.profissional_id
            LEFT JOIN areas_interesse ai ON pai.area_interesse_id = ai.id
            LEFT JOIN profissionais_areas_atuacao paa ON p.id = paa.profissional_id
            LEFT JOIN areas_atuacao aa ON paa.area_atuacao_id = aa.id
            """

            where_clauses = []
            params = []

            if filtros:
                if 'nome' in filtros:
                    where_clauses.append("LOWER(p.nome) LIKE %s")
                    params.append(f"%{filtros['nome'].lower()}%")
                if 'profissao' in filtros:
                    where_clauses.append("LOWER(prof.nome) LIKE %s")
                    params.append(f"%{filtros['profissao'].lower()}%")
                if 'genero' in filtros:
                    where_clauses.append("LOWER(g.nome) = %s")
                    params.append(filtros['genero'].lower())
                if 'area_atuacao' in filtros:
                    where_clauses.append("LOWER(aa.nome) LIKE %s")
                    params.append(f"%{filtros['area_atuacao'].lower()}%")

            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)

            query += " GROUP BY p.id"

            self.cursor.execute(query, params)
            return self.cursor.fetchall()

        finally:
            self._close_connection()
    def executar_query(self, query):
        """Executa uma query SQL personalizada"""
        try:
            self._get_connection()
            self.cursor.execute(query)
            return self.cursor.fetchall()
        finally:
            self._close_connection()