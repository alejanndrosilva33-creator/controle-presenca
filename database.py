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
            tipo TEXT NOT NULL CHECK(tipo IN ('Aluno', 'Funcionario'))
        )
    ''')

    # Migração para bancos existentes criados antes da coluna `tipo`
    cursor.execute("PRAGMA table_info(pessoas)")
    colunas = [coluna[1] for coluna in cursor.fetchall()]
    if 'tipo' not in colunas:
        cursor.execute("ALTER TABLE pessoas ADD COLUMN tipo TEXT NOT NULL DEFAULT 'Aluno'")

    # 2. Tabela de Aulas / Encontros
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS aulas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data DATE NOT NULL,
            descricao TEXT
        )
    ''')

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