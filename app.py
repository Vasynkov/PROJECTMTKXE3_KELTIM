import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import sqlite3
import random
import time
from werkzeug.security import generate_password_hash, check_password_hash
import google.generativeai as genai

load_dotenv()

# Configure Gemini AI
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-pro')
else:
    model = None

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'cryesix_ultra_secure_key_2026')

# Use absolute path for SQLite DB
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, os.getenv('DATABASE_URL', 'trigonometri.db'))

# --- Java-Style Backend Engine Class ---
class TrigonometryEngine:
    def __init__(self, db_path):
        self.db_path = db_path

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def fetch_questions(self, count=20):
        conn = self.get_connection()
        try:
            all_q = conn.execute('SELECT * FROM questions').fetchall()
            if len(all_q) < count: count = len(all_q)
            selected = random.sample(all_q, count)
            return [dict(q) for q in selected]
        finally:
            conn.close()

    def save_score(self, name, score, time_taken, accuracy):
        conn = self.get_connection()
        try:
            conn.execute('INSERT INTO scoreboard (name, score, time_taken, accuracy) VALUES (?, ?, ?, ?)',
                         (name, score, time_taken, accuracy))
            conn.commit()
        finally:
            conn.close()

    def get_top_scores(self, limit=10):
        conn = self.get_connection()
        try:
            scores = conn.execute('SELECT * FROM scoreboard ORDER BY score DESC, time_taken ASC LIMIT ?', (limit,)).fetchall()
            return [dict(s) for s in scores]
        finally:
            conn.close()

engine = TrigonometryEngine(DB_PATH)

# --- Routes ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/learn')
def learn():
    return render_template('learn.html')

@app.route('/api/gemini_study', methods=['POST'])
def gemini_study():
    if not model:
        return jsonify({"summary": "Gemini API Key tidak terdeteksi. Silakan hubungi admin untuk aktivasi fitur AI!"})
    
    topic = request.json.get('topic', 'Trigonometri dasar')
    prompt = f"Berikan penjelasan singkat dan super menarik ala guru matematika gaul tentang {topic}. Sertakan tips cepat untuk menghafal rumus. Gunakan bahasa Indonesia yang santai tapi edukatif."
    
    try:
        response = model.generate_content(prompt)
        return jsonify({"summary": response.text})
    except Exception as e:
        return jsonify({"summary": f"Gagal menghubungi Gemini: {str(e)}"})

@app.route('/start_game', methods=['POST'])
def start_game():
    name = request.form.get('player_name')
    if not name: name = "Guest Player"
    
    session['player_name'] = name
    session['score'] = 0
    session['start_time'] = time.time()
    session['streak'] = 0
    session['power_ups'] = ['Double Points', 'Eraser', 'Shield']
    session['active_power_up'] = None
    
    try:
        questions = engine.fetch_questions(20)
        session['question_indices'] = [q['id'] for q in questions]
        session['total_questions'] = len(questions)
        session['current_q_idx'] = 0
        session['correct_count'] = 0
        return redirect(url_for('game'))
    except Exception as e:
        return f"System Error: {e}", 500

@app.route('/game')
def game():
    if 'question_indices' not in session:
        return redirect(url_for('home'))
    
    idx = session['current_q_idx']
    total = session.get('total_questions', 20)
    
    if idx >= total: return redirect(url_for('finish'))
    
    q_id = session['question_indices'][idx]
    conn = engine.get_connection()
    question = conn.execute('SELECT * FROM questions WHERE id = ?', (q_id,)).fetchone()
    conn.close()
    
    return render_template('game.html', 
                           question=dict(question), 
                           q_num=idx+1, 
                           total_q=total,
                           power_ups=session.get('power_ups', []),
                           streak=session.get('streak', 0),
                           score=session.get('score', 0))

@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    user_answer = request.form.get('answer')
    q_id = request.form.get('q_id')
    
    conn = engine.get_connection()
    q = conn.execute('SELECT * FROM questions WHERE id = ?', (q_id,)).fetchone()
    conn.close()
    
    is_correct = (user_answer == q['answer'])
    points = 10
    bonus = 0
    active_pu = session.get('active_power_up')
    
    if is_correct:
        session['streak'] += 1
        session['correct_count'] += 1
        if session['streak'] >= 3: bonus += 5
        if active_pu == 'Double Points': points *= 2
        session['score'] += (points + bonus)
    else:
        if active_pu != 'Shield': session['streak'] = 0
            
    session['active_power_up'] = None
    session['current_q_idx'] += 1
    session.modified = True
    
    return jsonify({
        "correct": is_correct,
        "answer": q['answer'],
        "explanation": q['explanation'],
        "score": session['score'],
        "streak": session['streak'],
        "points_gained": points + bonus if is_correct else 0
    })

@app.route('/use_powerup', methods=['POST'])
def use_powerup():
    power_up = request.json.get('power_up')
    if power_up in session.get('power_ups', []):
        session['active_power_up'] = power_up
        session['power_ups'].remove(power_up)
        session.modified = True
        return jsonify({"success": True, "message": f"{power_up} Activated!"})
    return jsonify({"success": False})

@app.route('/finish')
def finish():
    player_name = session.get('player_name', 'Guest')
    score = session.get('score', 0)
    time_taken = round(time.time() - session.get('start_time', time.time()), 2)
    total = session.get('total_questions', 20)
    correct = session.get('correct_count', 0)
    accuracy = (correct / total) * 100 if total > 0 else 0
    
    engine.save_score(player_name, score, time_taken, accuracy)
    return render_template('finish.html', name=player_name, score=score, time=time_taken, acc=accuracy, correct=correct, total=total)

@app.route('/scoreboard_data')
def scoreboard_data():
    return jsonify(engine.get_top_scores())

# --- Admin Section ---
ADMIN_USER = os.getenv('ADMIN_USERNAME', 'admin')
DEFAULT_HASH = generate_password_hash(os.getenv('ADMIN_PASSWORD', 'password'))

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        usn = request.form.get('username')
        pwd = request.form.get('password')
        if usn == ADMIN_USER and check_password_hash(DEFAULT_HASH, pwd):
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        return render_template('admin_login.html', error="Invalid Credentials!")
    return render_template('admin_login.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    if not session.get('admin'): return redirect(url_for('admin_login'))
    conn = engine.get_connection()
    scores = conn.execute('SELECT * FROM scoreboard ORDER BY date_played DESC').fetchall()
    conn.close()
    return render_template('admin_dashboard.html', scores=scores)

@app.route('/easter_egg')
def easter_egg():
    return render_template('easter_egg.html')

@app.context_processor
def inject_school_info():
    return {
        "school_logo": "/static/img/logo_sman4.jpeg",
        "school_name": "SMAN 4 Jakarta",
        "school_loc": "Jl. Batu III No. 3, Gambir, Jakarta Pusat",
        "project_title": "TrigoQuest Cyber-Quizizz"
    }

if __name__ == '__main__':
    app.run(debug=True, port=5000)


if __name__ == '__main__':
    app.run(debug=True, port=5000)


if __name__ == '__main__':
    app.run(debug=True, port=5000)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
