import sqlite3

def conectar_banco():
    """Conecta ao arquivo de banco de dados SQLite."""
    # O SQLite criará o arquivo 'presenca.db' automaticamente na pasta do projeto
    conn = sqlite3.connect('presenca.db')
    # Permite acessar as colunas pelos nomes (ex: linha['nome'])
    conn.row_factory = sqlite3.Row 
    return conn

def criar_tabelas():
    """Cria a estrutura de tabelas no banco de dados se elas ainda não existirem."""
    conn = conectar_banco()
    cursor = conn.cursor()

    # 1. Tabela de Pessoas (Alunos / Funcionários)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pessoas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            matricula TEXT UNIQUE,
            turma_setor TEXT,
            tipo TEXT NOT NULL CHECK(tipo IN ('Aluno', 'Funcionario')),
            ativo INTEGER NOT NULL DEFAULT 1,
            visivel_relatorio INTEGER NOT NULL DEFAULT 1
        )
    ''')

    # Migração para bancos existentes criados antes das colunas novas
    cursor.execute("PRAGMA table_info(pessoas)")
    colunas = [coluna[1] for coluna in cursor.fetchall()]
    if 'tipo' not in colunas:
        cursor.execute("ALTER TABLE pessoas ADD COLUMN tipo TEXT NOT NULL DEFAULT 'Aluno'")
    if 'ativo' not in colunas:
        cursor.execute("ALTER TABLE pessoas ADD COLUMN ativo INTEGER NOT NULL DEFAULT 1")
    if 'visivel_relatorio' not in colunas:
        cursor.execute("ALTER TABLE pessoas ADD COLUMN visivel_relatorio INTEGER NOT NULL DEFAULT 1")

    # 2. Tabela de Aulas / Encontros
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS aulas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data DATE NOT NULL,
            descricao TEXT
        )
    ''')

    # Migração para remover duplicatas antigas de data no histórico
    cursor.execute('''
        SELECT data, COUNT(*) AS total
        FROM aulas
        GROUP BY data
        HAVING COUNT(*) > 1
    ''')
    duplicatas = cursor.fetchall()

    for linha in duplicatas:
        data_duplicada = linha['data']

        cursor.execute('SELECT id FROM aulas WHERE data = ? ORDER BY id', (data_duplicada,))
        ids = [row['id'] for row in cursor.fetchall()]
        id_mais_antigo = ids[0]
        ids_repetidos = ids[1:]

        for id_repetido in ids_repetidos:
            cursor.execute('SELECT id, pessoa_id, status FROM presencas WHERE aula_id = ?', (id_repetido,))
            registros = cursor.fetchall()

            for registro in registros:
                cursor.execute(
                    'SELECT id, status FROM presencas WHERE pessoa_id = ? AND aula_id = ?',
                    (registro['pessoa_id'], id_mais_antigo)
                )
                registro_canonico = cursor.fetchone()

                if registro_canonico is None:
                    cursor.execute(
                        'UPDATE presencas SET aula_id = ? WHERE id = ?',
                        (id_mais_antigo, registro['id'])
                    )
                else:
                    prioridade = {'Presente': 3, 'Justificado': 2, 'Falta': 1}
                    status_atual = registro_canonico['status']
                    status_novo = registro['status']

                    if prioridade.get(status_novo, 0) > prioridade.get(status_atual, 0):
                        cursor.execute(
                            'UPDATE presencas SET status = ? WHERE id = ?',
                            (status_novo, registro_canonico['id'])
                        )

                    cursor.execute('DELETE FROM presencas WHERE id = ?', (registro['id'],))

        if ids_repetidos:
            placeholders = ', '.join('?' for _ in ids_repetidos)
            cursor.execute(f'DELETE FROM aulas WHERE id IN ({placeholders})', ids_repetidos)

    # Garante unicidade real de data para impedir duas chamadas na mesma data
    cursor.execute('DROP INDEX IF EXISTS idx_aulas_data')
    cursor.execute("CREATE UNIQUE INDEX idx_aulas_data ON aulas(data)")

    # 3. Tabela de Presenças (Relaciona Pessoas com Aulas)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS presencas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pessoa_id INTEGER NOT NULL,
            aula_id INTEGER NOT NULL,
            status TEXT CHECK(status IN ('Presente', 'Falta', 'Justificado')) NOT NULL,
            observacao TEXT,
            FOREIGN KEY (pessoa_id) REFERENCES pessoas (id),
            FOREIGN KEY (aula_id) REFERENCES aulas (id),
            UNIQUE(pessoa_id, aula_id) -- Evita registrar a mesma pessoa duas vezes na mesma aula
        )
    ''')

    conn.commit()
    conn.close()
    print("Banco de dados e tabelas criados com sucesso!")

# Executa a criação das tabelas ao rodar este arquivo diretamente
if __name__ == '__main__':
    criar_tabelas()