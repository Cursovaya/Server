import os
import sqlite3
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), 'ldpr_edo.db')
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT,
            login TEXT UNIQUE,
            password TEXT,
            role TEXT,
            department_id INTEGER
        );
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            head_id INTEGER
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT,
            priority TEXT,
            status TEXT,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deadline DATE,
            internal_deadline DATE,
            assigned_department_id INTEGER,
            assigned_executor_id INTEGER
        );
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            filename TEXT,
            filepath TEXT
        );
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message TEXT,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS order_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            action TEXT,
            user_name TEXT,
            user_role TEXT,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    
    # Создаём тестовых пользователей, если их нет
    users = [
        ('Администратор', 'admin', 'admin123', 'admin'),
        ('Помощник', 'assistant', '123', 'assistant'),
        ('Руководитель ЦА', 'head_central', '123', 'head_central'),
        ('Секретариат ЦА', 'secretary', '123', 'secretary')
    ]
    for full_name, login, password, role in users:
        cur.execute("SELECT id FROM users WHERE login=?", (login,))
        if not cur.fetchone():
            cur.execute("INSERT INTO users (full_name, login, password, role) VALUES (?,?,?,?)",
                        (full_name, login, password, role))
    
    conn.commit()
    conn.close()

init_db()

@app.route('/api/execute', methods=['POST'])
def execute_sql():
    data = request.json
    query = data['query']
    params = data.get('params', [])
    commit = data.get('commit', False)
    fetch = data.get('fetch', False)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        if commit:
            conn.commit()
            result = cur.lastrowid
        elif fetch:
            rows = cur.fetchall()
            result = [list(row) for row in rows]
        else:
            result = None
        cur.close()
        conn.close()
        return jsonify({'result': result, 'success': True})
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/api/upload_files', methods=['POST'])
def upload_files():
    order_id = request.form['order_id']
    files = request.files.getlist('files')
    for f in files:
        if f.filename:
            filename = f.filename
            dest = os.path.join(UPLOAD_FOLDER, f"{order_id}_{filename}")
            f.save(dest)
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("INSERT INTO files (order_id, filename, filepath) VALUES (?,?,?)",
                        (order_id, filename, dest))
            conn.commit()
            conn.close()
    return jsonify({'success': True})

@app.route('/api/upload_result', methods=['POST'])
def upload_result():
    order_id = request.form['order_id']
    file = request.files['file']
    if file and file.filename:
        filename = file.filename
        dest = os.path.join(UPLOAD_FOLDER, f"{order_id}_{filename}")
        file.save(dest)
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("INSERT INTO files (order_id, filename, filepath) VALUES (?,?,?)",
                    (order_id, filename, dest))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    return jsonify({'error': 'No file'}), 400

@app.route('/api/download/<path:filename>', methods=['GET'])
def download_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000, debug=False)
