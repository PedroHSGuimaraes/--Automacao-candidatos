import json
from datetime import datetime
from src.database.database_connection import DatabaseConnection


class DataService:
    def __init__(self):
        self.conn = None
        self.cursor = None

    def _get_connection(self):
        self.conn, self.cursor = DatabaseConnection.get_connection()

    def _close_connection(self):
        DatabaseConnection.close_connection(self.conn, self.cursor)

    def _get_or_create_faculdade(self, nome, cidade='', estado=''):
        nome = nome.lower().strip()
        self.cursor.execute(
            "SELECT id FROM faculdades WHERE LOWER(nome) = %s",
            (nome,)
        )
        result = self.cursor.fetchone()

        if result:
            return result['id']

        self.cursor.execute(
            "INSERT INTO faculdades (nome, cidade, estado) VALUES (%s, %s, %s)",
            (nome, cidade.lower(), estado.lower())
        )
        return self.cursor.lastrowid

    def _get_or_create_genero(self, genero_data):
        try:
            if isinstance(genero_data, str):
                nome = genero_data.lower().strip()
                descricao = ""
            else:
                nome = genero_data.get('nome', 'não identificado').lower().strip()
                descricao = genero_data.get('descricao', '').lower().strip()

            if nome not in ['masculino', 'feminino', 'não identificado']:
                nome = 'não identificado'

            self.cursor.execute(
                "SELECT id FROM generos WHERE LOWER(nome) = %s",
                (nome,)
            )
            resultado = self.cursor.fetchone()

            if resultado:
                genero_id = resultado['id']
                if descricao:
                    self.cursor.execute(
                        "UPDATE generos SET descricao = %s WHERE id = %s",
                        (descricao, genero_id)
                    )
                return genero_id

            self.cursor.execute(
                "INSERT INTO generos (nome, descricao) VALUES (%s, %s)",
                (nome, descricao)
            )
            return self.cursor.lastrowid

        except Exception as e:
            print(f"Erro ao buscar/criar gênero: {e}")
            self.cursor.execute(
                "SELECT id FROM generos WHERE nome = 'não identificado'"
            )
            return self.cursor.fetchone()['id']

    def _get_or_create_idioma(self, nome):
        try:
            nome = nome.lower().strip()
            self.cursor.execute(
                "SELECT id FROM idiomas WHERE LOWER(nome) = %s",
                (nome,)
            )
            result = self.cursor.fetchone()

            if result:
                return result['id']

            self.cursor.execute(
                "INSERT INTO idiomas (nome) VALUES (%s)",
                (nome,)
            )
            return self.cursor.lastrowid

        except Exception as e:
            print(f"Erro ao buscar/criar idioma: {e}")
            raise

    def _salvar_idioma(self, profissional_id, idioma):
        try:
            self.cursor.execute(
                "SELECT id FROM idiomas WHERE LOWER(nome) = %s",
                (idioma['nome'].lower(),)
            )
            resultado = self.cursor.fetchone()

            if resultado:
                idioma_id = resultado['id']
            else:
                self.cursor.execute(
                    "INSERT INTO idiomas (nome, codigo) VALUES (%s, %s)",
                    (idioma['nome'].lower(), idioma.get('codigo', ''))
                )
                idioma_id = self.cursor.lastrowid

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
        try:
            nome = area['nome'].lower().strip()

            # Primeiro busca área exata
            self.cursor.execute(
                "SELECT id FROM areas_interesse WHERE LOWER(nome) = %s",
                (nome,)
            )
            resultado = self.cursor.fetchone()

            if resultado:
                area_id = resultado['id']
                # Atualiza métricas de uso
                self.cursor.execute("""
                    UPDATE areas_interesse 
                    SET total_uso = COALESCE(total_uso, 0) + 1,
                        ultima_atualizacao = NOW(),
                        termos_similares = CONCAT_WS(',', termos_similares, %s)
                    WHERE id = %s
                """, (area.get('termos_relacionados', ''), area_id))
            else:
                # Busca similares
                self.cursor.execute("""
                    SELECT id, nome
                    FROM areas_interesse 
                    WHERE LOWER(nome) LIKE %s
                    OR LOWER(descricao) LIKE %s
                    OR MATCH(nome, descricao, termos_similares) AGAINST(%s IN BOOLEAN MODE)
                    ORDER BY total_uso DESC
                    LIMIT 1
                """, (f"%{nome}%", f"%{nome}%", nome))

                similar = self.cursor.fetchone()
                if similar:
                    area_id = similar['id']
                    # Atualiza área existente
                    self.cursor.execute("""
                        UPDATE areas_interesse 
                        SET total_uso = COALESCE(total_uso, 0) + 1,
                            ultima_atualizacao = NOW(),
                            termos_similares = CONCAT_WS(',', termos_similares, %s)
                        WHERE id = %s
                    """, (nome, area_id))
                else:
                    # Cria nova área
                    self.cursor.execute("""
                        INSERT INTO areas_interesse 
                        (nome, descricao, termos_similares, total_uso) 
                        VALUES (%s, %s, %s, 1)
                    """, (
                        nome,
                        area.get('descricao', f"Área de interesse identificada a partir do termo: {nome}"),
                        area.get('termos_relacionados', '')
                    ))
                    area_id = self.cursor.lastrowid

            # Insere o relacionamento
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
            print(f"Erro ao salvar área de interesse '{nome}': {e}")
            raise

    def _salvar_area_atuacao(self, profissional_id, area):
        try:
            nome = area['nome'].lower().strip()

            # Primeiro busca área exata
            self.cursor.execute(
                "SELECT id FROM areas_atuacao WHERE LOWER(nome) = %s",
                (nome,)
            )
            resultado = self.cursor.fetchone()

            if resultado:
                area_id = resultado['id']
                # Atualiza métricas de uso
                self.cursor.execute("""
                    UPDATE areas_atuacao 
                    SET total_uso = COALESCE(total_uso, 0) + 1,
                        ultima_atualizacao = NOW(),
                        termos_similares = CONCAT_WS(',', termos_similares, %s)
                    WHERE id = %s
                """, (area.get('termos_relacionados', ''), area_id))
            else:
                # Busca similares
                self.cursor.execute("""
                    SELECT id, nome
                    FROM areas_atuacao 
                    WHERE LOWER(nome) LIKE %s
                    OR LOWER(descricao) LIKE %s
                    OR MATCH(nome, descricao, termos_similares) AGAINST(%s IN BOOLEAN MODE)
                    ORDER BY total_uso DESC
                    LIMIT 1
                """, (f"%{nome}%", f"%{nome}%", nome))

                similar = self.cursor.fetchone()
                if similar:
                    area_id = similar['id']
                    # Atualiza área existente
                    self.cursor.execute("""
                        UPDATE areas_atuacao 
                        SET total_uso = COALESCE(total_uso, 0) + 1,
                            ultima_atualizacao = NOW(),
                            termos_similares = CONCAT_WS(',', termos_similares, %s)
                        WHERE id = %s
                    """, (nome, area_id))
                else:
                    # Cria nova área
                    self.cursor.execute("""
                        INSERT INTO areas_atuacao 
                        (nome, descricao, termos_similares, total_uso) 
                        VALUES (%s, %s, %s, 1)
                    """, (
                        nome,
                        area.get('descricao', f"Área de atuação identificada a partir do termo: {nome}"),
                        area.get('termos_relacionados', '')
                    ))
                    area_id = self.cursor.lastrowid

            # Insere o relacionamento
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
            print(f"Erro ao salvar área de atuação '{nome}': {e}")
            raise

    def salvar_profissional(self, dados, texto_pdf):
        try:
            self._get_connection()

            faculdade_id = self._get_or_create_faculdade(
                dados['faculdade']['nome'],
                dados['faculdade']['cidade'],
                dados['faculdade']['estado']
            )
            genero_id = self._get_or_create_genero(dados['profissional']['genero'])

            idioma_principal_id = None
            nivel_idioma_principal = None
            if dados['idiomas']:
                idioma_principal = next(
                    (idioma for idioma in dados['idiomas'] if 'ingles' in idioma['nome'].lower()),
                    dados['idiomas'][0]
                )
                idioma_principal_id = self._get_or_create_idioma(idioma_principal['nome'])
                nivel_idioma_principal = idioma_principal.get('nivel', '').lower()

            query = """
                INSERT INTO profissionais (
                    nome, email, telefone, endereco, portfolio_url, linkedin_url,
                    github_url, cargo_atual, faculdade_id, genero_id, pdf_curriculo,
                    idade, pretensao_salarial, disponibilidade, tipo_contrato,
                    observacoes_ia, campos_dinamicos, idioma_principal_id, 
                    nivel_idioma_principal, habilidades
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s
                )
            """
            valores = (
                dados['profissional']['nome'],
                dados['profissional']['email'],
                dados['profissional']['telefone'],
                dados['profissional']['endereco'],
                dados['profissional']['portfolio_url'],
                dados['profissional']['linkedin_url'],
                dados['profissional']['github_url'],
                dados['profissional'].get('cargo_atual', ''),
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
                nivel_idioma_principal,
                json.dumps(dados['profissional']['habilidades'])
            )
            self.cursor.execute(query, valores)
            profissional_id = self.cursor.lastrowid

            for idioma in dados['idiomas']:
                self._salvar_idioma(profissional_id, idioma)

            for area in dados['areas_interesse']:
                self._salvar_area_interesse(profissional_id, area)

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

    def buscar_profissionais(self, filtros=None):
        try:
            self._get_connection()
            query = """
            SELECT 
                p.*,
                p.cargo_atual,
                g.nome as genero,
                f.nome as faculdade,
                i.nome as idioma_principal,
                GROUP_CONCAT(DISTINCT CONCAT(i2.nome, ' (', pi.nivel, ')')) as idiomas,
                GROUP_CONCAT(DISTINCT ai.nome) as areas_interesse,
                GROUP_CONCAT(DISTINCT CONCAT(aa.nome, ' (', paa.anos_experiencia, ' anos)')) as areas_atuacao,
                GROUP_CONCAT(DISTINCT CONCAT(paa.ultimo_cargo, ' em ', paa.ultima_empresa)) as experiencias,
                GROUP_CONCAT(DISTINCT paa.descricao_atividades) as descricao_experiencias
            FROM profissionais p
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
                    where_clauses.append("(LOWER(p.nome) LIKE %s)")
                    params.append(f"%{filtros['nome'].lower()}%")

                if 'cargo' in filtros:
                    where_clauses.append("""(
                        LOWER(p.cargo_atual) LIKE %s OR 
                        LOWER(paa.ultimo_cargo) LIKE %s OR
                        JSON_SEARCH(LOWER(p.habilidades), 'one', %s) IS NOT NULL
                    )""")
                    termo = f"%{filtros['cargo'].lower()}%"
                    params.extend([termo, termo, termo])

                if 'genero' in filtros:
                    where_clauses.append("LOWER(g.nome) = %s")
                    params.append(filtros['genero'].lower())

                if 'area_atuacao' in filtros:
                    where_clauses.append("""(
                        LOWER(aa.nome) LIKE %s OR 
                        LOWER(paa.descricao_atividades) LIKE %s
                    )""")
                    termo = f"%{filtros['area_atuacao'].lower()}%"
                    params.extend([termo, termo])

                if 'idioma' in filtros:
                    where_clauses.append("""(
                        LOWER(i.nome) = %s OR 
                        LOWER(i2.nome) = %s
                    )""")
                    params.extend([filtros['idioma'].lower(), filtros['idioma'].lower()])

                if 'experiencia_minima' in filtros:
                    where_clauses.append("paa.anos_experiencia >= %s")
                    params.append(filtros['experiencia_minima'])

                if 'habilidade' in filtros:
                    where_clauses.append("""(
                        JSON_SEARCH(LOWER(p.habilidades), 'one', %s) IS NOT NULL OR
                        LOWER(paa.descricao_atividades) LIKE %s
                    )""")
                    termo = f"%{filtros['habilidade'].lower()}%"
                    params.extend([termo, termo])

                if 'cidade' in filtros:
                    where_clauses.append("LOWER(p.endereco) LIKE %s")
                    params.append(f"%{filtros['cidade'].lower()}%")

                if 'pretensao_maxima' in filtros:
                    where_clauses.append("p.pretensao_salarial <= %s")
                    params.append(filtros['pretensao_maxima'])

                if 'disponibilidade' in filtros:
                    where_clauses.append("LOWER(p.disponibilidade) = %s")
                    params.append(filtros['disponibilidade'].lower())

            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)

            query += " GROUP BY p.id"

            if 'ordenar_por' in filtros:
                ordem = filtros['ordenar_por']
                if ordem == 'experiencia':
                    query += " ORDER BY paa.anos_experiencia DESC"
                elif ordem == 'pretensao':
                    query += " ORDER BY p.pretensao_salarial ASC"
                elif ordem == 'mais_recente':
                    query += " ORDER BY p.data_criacao DESC"

            if 'limite' in filtros:
                query += " LIMIT %s"
                params.append(filtros['limite'])

            self.cursor.execute(query, params)
            return self.cursor.fetchall()

        finally:
            self._close_connection()

    def executar_query(self, query):
        try:
            self._get_connection()
            self.cursor.execute(query)
            return self.cursor.fetchall()
        finally:
            self._close_connection()