from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from database import conectar_banco, criar_tabelas
from datetime import date

app = Flask(__name__)
criar_tabelas()

# --- ROTA 1: Página Inicial (Exibe Pessoas e Formulário de Presença) ---
@app.route('/')
def index():
    conn = conectar_banco()
    cursor = conn.cursor()
    
    # Busca somente pessoas ativas na listagem da chamada
    cursor.execute('SELECT * FROM pessoas WHERE ativo = 1 ORDER BY nome')
    pessoas = cursor.fetchall()
    conn.close()

    data_hoje = date.today().strftime('%Y-%m-%d')
    return render_template('index.html', pessoas=pessoas, data_hoje=data_hoje)


# --- ROTA 2: Registrar a Chamada do Dia ---
@app.route('/registrar_presenca', methods=['POST'])
def registrar_presenca():
    data_aula = request.form['data']
    descricao = request.form.get('descricao', 'Chamada Diária')
    
    conn = conectar_banco()
    cursor = conn.cursor()

    # 1. Cria a aula apenas se a data ainda não existir; se já existir, reaproveita a mesma aula
    cursor.execute('INSERT OR IGNORE INTO aulas (data, descricao) VALUES (?, ?)', (data_aula, descricao))
    cursor.execute('SELECT id FROM aulas WHERE data = ?', (data_aula,))
    aula = cursor.fetchone()
    aula_id = aula['id']

    # 2. Registra o status (Presente/Falta) para cada pessoa ativa
    cursor.execute('SELECT id FROM pessoas WHERE ativo = 1')
    pessoas = cursor.fetchall()

    for pessoa in pessoas:
        pessoa_id = pessoa['id']
        status = request.form.get(f'status_{pessoa_id}', 'Falta')
        
        cursor.execute('''
            INSERT INTO presencas (pessoa_id, aula_id, status)
            VALUES (?, ?, ?)
            ON CONFLICT(pessoa_id, aula_id)
            DO UPDATE SET status = excluded.status
        ''', (pessoa_id, aula_id, status))

    conn.commit()
    conn.close()
    return redirect(url_for('index'))


# --- ROTA 3: Tela de Cadastro de Pessoas ---
@app.route('/cadastrar', methods=['GET', 'POST'])
def cadastrar():
    if request.method == 'POST':
        nome = request.form['nome']
        matricula = request.form['matricula']
        turma_setor = request.form['turma_setor']
        tipo = request.form.get('tipo', 'Aluno')

        conn = conectar_banco()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO pessoas (nome, matricula, turma_setor, tipo, ativo, visivel_relatorio)
            VALUES (?, ?, ?, ?, 1, 1)
        ''', (nome, matricula, turma_setor, tipo))
        conn.commit()
        conn.close()

        return redirect(url_for('index'))

    return render_template('cadastrar.html')

# --- ROTA 4: Editar Pessoa Cadastrada ---
@app.route('/editar_pessoa/<int:pessoa_id>', methods=['GET', 'POST'])
def editar_pessoa(pessoa_id):
    conn = conectar_banco()
    cursor = conn.cursor()

    if request.method == 'POST':
        nome = request.form['nome']
        matricula = request.form['matricula']
        turma_setor = request.form['turma_setor']
        tipo = request.form.get('tipo', 'Aluno')

        cursor.execute('''
            UPDATE pessoas
            SET nome = ?, matricula = ?, turma_setor = ?, tipo = ?
            WHERE id = ?
        ''', (nome, matricula, turma_setor, tipo, pessoa_id))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    cursor.execute('SELECT * FROM pessoas WHERE id = ?', (pessoa_id,))
    pessoa = cursor.fetchone()
    conn.close()

    return render_template('editar_pessoa.html', pessoa=pessoa)

# --- ROTA 5: Excluir Pessoa Cadastrada (lista da chamada) ---
@app.route('/excluir_pessoa/<int:pessoa_id>', methods=['POST'])
def excluir_pessoa(pessoa_id):
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute('UPDATE pessoas SET ativo = 0 WHERE id = ?', (pessoa_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

# --- ROTA 5B: Excluir Pessoa apenas do relatório ---
@app.route('/excluir_pessoa_relatorio/<int:pessoa_id>', methods=['POST'])
def excluir_pessoa_relatorio(pessoa_id):
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute('UPDATE pessoas SET visivel_relatorio = 0 WHERE id = ?', (pessoa_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('relatorio'))

# --- ROTA 6: Tela de Relatórios e Histórico ---
@app.route('/relatorio')
def relatorio():
    conn = conectar_banco()
    cursor = conn.cursor()

    # Consulta avançada que conta presenças e faltas agrupadas por pessoa
    cursor.execute('''
        SELECT 
            p.id,
            p.nome,
            p.turma_setor,
            COUNT(CASE WHEN pr.status = 'Presente' THEN 1 END) as presencas,
            COUNT(CASE WHEN pr.status = 'Falta' THEN 1 END) as faltas,
            COUNT(pr.id) as total_aulas
        FROM pessoas p
        LEFT JOIN presencas pr ON p.id = pr.pessoa_id
        WHERE p.visivel_relatorio = 1
        GROUP BY p.id
        ORDER BY p.nome
    ''')
    dados = cursor.fetchall()
    conn.close()

    return render_template('relatorio.html', dados=dados)

if __name__ == '__main__':
    app.run(debug=True)