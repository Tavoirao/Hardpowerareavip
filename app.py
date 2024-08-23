import os
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user
import MySQLdb
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Função para obter a conexão com o banco de dados MySQL
def get_db_connection():
    return MySQLdb.connect(
        host='bancohardpw2.mysql.dbaas.com.br',
        user='bancohardpw2',
        passwd='Q@or2tigQ@ZM',
        db='bancohardpw2',
        port=3306,
        connect_timeout=60,  # Aumenta o tempo limite de conexão
        read_timeout=60,     # Aumenta o tempo limite de leitura
        write_timeout=60     # Aumenta o tempo limite de gravação
    )

# Criando a conexão inicial
connection = get_db_connection()

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'index'

class User(UserMixin):
    def __init__(self, id, username, is_admin):
        self.id = id
        self.username = username
        self.is_admin = is_admin

@login_manager.user_loader
def load_user(user_id):
    global connection  # Usar a variável global `connection`
    cursor = connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        connection.ping(True)  # Verifica e reconecta se necessário
        cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
        account = cursor.fetchone()
        if account:
            return User(id=account['id'], username=account['username'], is_admin=account['is_admin'])
    except MySQLdb.OperationalError as e:
        if e.args[0] == 2006:  # Error 2006: MySQL server has gone away
            connection = get_db_connection()  # Reconecte e redefina `connection`
            cursor = connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
            account = cursor.fetchone()
            if account:
                return User(id=account['id'], username=account['username'], is_admin=account['is_admin'])
        else:
            raise
    return None

def generate_unique_filename(directory, filename):
    """Gera um nome de arquivo único no diretório especificado."""
    base, extension = os.path.splitext(filename)
    counter = 1
    unique_filename = filename

    while os.path.exists(os.path.join(directory, unique_filename)):
        unique_filename = f"{base} ({counter}){extension}"
        counter += 1

    return unique_filename

@app.route('/', methods=['GET', 'POST'])
def index():
    global connection  # Usar a variável global `connection`
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor = connection.cursor(MySQLdb.cursors.DictCursor)
        
        try:
            connection.ping(True)  # Verifica e reconecta se necessário
            cursor.execute('SELECT * FROM users WHERE username = %s AND password = %s', (username, password))
            account = cursor.fetchone()
            
            if account:
                user = User(id=account['id'], username=account['username'], is_admin=account['is_admin'])
                login_user(user)
                
                if user.is_admin:
                    return redirect(url_for('admin'))
                else:
                    return redirect(url_for('visitor'))
            else:
                flash('Login ou senha incorreto')
        except MySQLdb.OperationalError as e:
            if e.args[0] == 2006:  # Error 2006: MySQL server has gone away
                connection = get_db_connection()  # Reconecte e redefina `connection`
                cursor = connection.cursor(MySQLdb.cursors.DictCursor)
                cursor.execute('SELECT * FROM users WHERE username = %s AND password = %s', (username, password))
                account = cursor.fetchone()
                if account:
                    user = User(id=account['id'], username=account['username'], is_admin=account['is_admin'])
                    login_user(user)
                    
                    if user.is_admin:
                        return redirect(url_for('admin'))
                    else:
                        return redirect(url_for('visitor'))
                else:
                    flash('Login ou senha incorreto')
            else:
                flash(f"Erro ao conectar ao banco de dados: {e}")
                return redirect(url_for('index'))
        
    return render_template('index.html')

@app.route('/visitor')
@login_required
def visitor():
    return render_template('visitor.html')

@app.route('/abrir_os', methods=['GET', 'POST'])
@login_required
def abrir_os():
    global connection  # Usar a variável global `connection`
    cursor = connection.cursor(MySQLdb.cursors.DictCursor)
    
    username = current_user.username

    cursor.execute('SELECT COUNT(*) as os_count FROM os WHERE username = %s', (username,))
    os_count = cursor.fetchone()['os_count'] + 1
    os_number = f"OS{os_count}"
    
    cursor.execute('SELECT * FROM products')
    products = cursor.fetchall()

    if request.method == 'POST':
        guarantee = request.form['guarantee']
        serial_number = request.form['serial_number']
        owner_name = request.form['owner_name']
        owner_phone = request.form['owner_phone']
        product_id = request.form['product']
        observations = request.form['observations']
        files = request.files.getlist('files')

        cursor.execute('''
            INSERT INTO os (username, os_number, guarantee, serial_number, owner_name, owner_phone, product_id, observations)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (username, os_number, guarantee, serial_number, owner_name, owner_phone, product_id, observations))
        os_id = cursor.lastrowid

        # Caminho absoluto para o diretório de uploads dentro de static
        upload_directory = os.path.join(app.root_path, 'static', 'uploads')
        if not os.path.exists(upload_directory):
            os.makedirs(upload_directory)

        for file in files:
            unique_filename = generate_unique_filename(upload_directory, file.filename)
            file.save(os.path.join(upload_directory, unique_filename))
            cursor.execute('INSERT INTO os_files (os_id, filename) VALUES (%s, %s)', (os_id, unique_filename))
        
        connection.commit()
        flash('O.S. aberta com sucesso!')
        return redirect(url_for('visitor'))

    return render_template('abrir_os.html', os_number=os_number, products=products)

@app.route('/admin')
@login_required
def admin():
    return render_template('admin.html')

@app.route('/responder_os', methods=['GET', 'POST'])
@login_required
def responder_os():
    global connection  # Usar a variável global `connection`
    if not current_user.is_admin:
        return redirect(url_for('visitor'))

    cursor = connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        os_id = request.form['os_id']
        final_verdict = request.form['is_warranty']
        justification = request.form['justification']

        cursor.execute('''
            INSERT INTO is_warranty_final (os_id, final_verdict, justification)
            VALUES (%s, %s, %s)
        ''', (os_id, final_verdict, justification))

        cursor.execute('''
            UPDATE os
            SET processed = 1
            WHERE id = %s
        ''', (os_id,))

        connection.commit()
        flash('O.S. processada e arquivada com sucesso!')
        return redirect(url_for('responder_os'))

    cursor.execute('''
        SELECT os.*, products.product_name, products.impedance, products.size_in_inches, users.username
        FROM os 
        JOIN products ON os.product_id = products.id
        JOIN users ON os.username = users.username
        WHERE os.processed = 0
        ORDER BY os.created_at DESC
    ''')
    os_list = cursor.fetchall()

    for os in os_list:
        cursor.execute('SELECT filename FROM os_files WHERE os_id = %s', (os['id'],))
        os['files'] = cursor.fetchall()

    return render_template('responder_os.html', os_list=os_list)

@app.route('/os_antigas')
@login_required
def os_antigas():
    global connection  # Usar a variável global `connection`
    if not current_user.is_admin:
        return redirect(url_for('visitor'))

    cursor = connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute('''
        SELECT os.*, products.product_name, products.impedance, products.size_in_inches, users.username,
               is_warranty_final.final_verdict, is_warranty_final.justification
        FROM os 
        JOIN products ON os.product_id = products.id
        JOIN is_warranty_final ON os.id = is_warranty_final.os_id
        JOIN users ON os.username = users.username
        WHERE os.processed = 1
        ORDER BY os.created_at DESC
    ''')
    archived_os_list = cursor.fetchall()

    return render_template('os_antigas.html', archived_os_list=archived_os_list)

@app.route('/ver_resultado_os')
@login_required
def ver_resultado_os():
    global connection  # Usar a variável global `connection`
    cursor = connection.cursor(MySQLdb.cursors.DictCursor)
    
    cursor.execute('''
        SELECT os.*, products.product_name, products.impedance, products.size_in_inches, 
               is_warranty_final.final_verdict, is_warranty_final.justification
        FROM os 
        JOIN products ON os.product_id = products.id
        JOIN is_warranty_final ON os.id = is_warranty_final.os_id
        WHERE os.username = %s AND os.processed = 1
        ORDER BY os.created_at DESC
    ''', (current_user.username,))
    user_os_list = cursor.fetchall()

    return render_template('ver_resultado_os.html', user_os_list=user_os_list)

@app.route('/relatorio_mensal', methods=['GET', 'POST'])
@login_required
def relatorio_mensal():
    global connection  # Usar a variável global `connection`
    if not current_user.is_admin:
        return redirect(url_for('visitor'))

    cursor = connection.cursor(MySQLdb.cursors.DictCursor)
    relatorio = []
    total_geral = 0
    mes, ano = None, None

    if request.method == 'POST':
        data = request.form['data']
        mes, ano = data.split('/')
        mes = int(mes)
        ano = int(ano)
        
        cursor.execute('''
            SELECT os.username, products.product_name, products.impedance, products.size_in_inches, COUNT(os.id) as total
            FROM os 
            JOIN products ON os.product_id = products.id
            WHERE os.is_warranty = 'Sim' AND MONTH(os.created_at) = %s AND YEAR(os.created_at) = %s
            GROUP BY os.username, products.product_name, products.impedance, products.size_in_inches
        ''', (mes, ano))
        relatorio = cursor.fetchall()

        total_geral = sum([item['total'] for item in relatorio])

    return render_template('relatorio_mensal.html', relatorio=relatorio, total_geral=total_geral, mes=mes, ano=ano)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/back')
@login_required
def back():
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
