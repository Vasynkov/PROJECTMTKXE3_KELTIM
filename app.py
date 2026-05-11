import os
import sqlite3
import random
import time
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import google.generativeai as genai

# --- 1. ENVIRONMENT & SECURITY CONFIGURATION ---
load_dotenv()

app = Flask(__name__)
# Secret key is pulled from environment for security
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'default_fallback_secure_key_2026')

# Secure Admin Configuration
ADMIN_USER = os.getenv('ADMIN_USERNAME', 'admin')
# Use a pre-generated hash or generate one from the .env password
ADMIN_PWD_PLAIN = os.getenv('ADMIN_PASSWORD', 'password')
ADMIN_PWD_HASH = generate_password_hash(ADMIN_PWD_PLAIN)

# Gemini AI Configuration
GEMINI_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    ai_model = genai.GenerativeModel('gemini-pro')
else:
    ai_model = None

# Database Path - Optimized for Vercel
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'trigonometri.db')

# --- 2. HIGH-PERFORMANCE DATABASE ENGINE ---
class TrigoEngine:
    """
    Optimized for high-concurrency environments like Vercel.
    Uses context managers and careful error handling to prevent locks.
    """
    def __init__(self, path):
        self.path = path

    def get_conn(self, read_only=True):
        # On some environments, we use uri=True for shared cache or read-only modes
        if read_only:
            # Open in read-only mode to prevent 'database is locked' errors under high load
            return sqlite3.connect(f"file:{self.path}?mode=ro", uri=True)
        return sqlite3.connect(self.path)

    def fetch_all_questions(self):
        conn = self.get_conn(read_only=True)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.cursor()
            return [dict(row) for row in cursor.execute("SELECT * FROM questions").fetchall()]
        finally:
            conn.close()

    def get_question_by_id(self, q_id):
        conn = self.get_conn(read_only=True)
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute("SELECT * FROM questions WHERE id = ?", (q_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def submit_score(self, name, score, time_taken, accuracy):
        # Vercel filesystem is read-only; persistent writes to SQLite will fail.
        # We catch the error to keep the app running for the user.
        try:
            conn = self.get_conn(read_only=False)
            conn.execute("INSERT INTO scoreboard (name, score, time_taken, accuracy) VALUES (?, ?, ?, ?)",
                         (name, score, time_taken, accuracy))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"[DB LOG] Persistent write failed (Expected on Vercel): {e}")
            return False

    def get_leaderboard(self, limit=10):
        try:
            conn = self.get_conn(read_only=True)
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM scoreboard ORDER BY score DESC, time_taken ASC LIMIT ?", (limit,)).fetchall()
            conn.close()
            return [dict(r) for row in rows]
        except:
            return []

engine = TrigoEngine(DB_PATH)

# --- 3. PROJECT DATA ---
GROUP_MEMBERS = [
    {"name": "Aira Adekha Anfi", "no": 2},
    {"name": "Gilang Satria Pratama", "no": 10},
    {"name": "Irsanny Fadhil Kurnaefi", "no": 13},
    {"name": "Jafier Yusuf Putera", "no": 14},
    {"name": "Labib Lawahizh Ramadhani", "no": 18},
    {"name": "M. Atallah Rizal", "no": 20},
    {"name": "Raffi Putra Dwi Cahyana", "no": 26},
    {"name": "Shafira Bilqies Dermawan", "no": 30}
]

# --- 4. CORE ROUTES ---
@app.route('/')
def home():
    return render_template('index.html', members=GROUP_MEMBERS)

@app.route('/learn')
def learn():
    return render_template('learn.html', members=GROUP_MEMBERS)

@app.route('/start_game', methods=['POST', 'GET'])
def start_game():
    # User requested direct redirect to Wayground for the quiz
    return redirect("https://quizizz.com/join?query=Trigonometri+Kuadran+Kelas+10")

@app.route('/game')
def game():
    # Redirect to Wayground as well to ensure students don't use the old local game
    return redirect("https://quizizz.com/join?query=Trigonometri+Kuadran+Kelas+10")

@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    user_choice = request.form.get('answer')
    q_id = request.form.get('q_id')
    q_data = engine.get_question_by_id(q_id)
    
    is_correct = (user_choice == q_data['answer'])
    base_points = 10
    bonus = 0
    
    active_pu = session.get('active_power_up')
    
    if is_correct:
        session['streak'] += 1
        session['correct_count'] += 1
        if session['streak'] >= 3: bonus = 5
        if active_pu == 'Double Points': base_points *= 2
        session['score'] += (base_points + bonus)
    else:
        if active_pu != 'Shield Pulse': session['streak'] = 0
            
    session['active_power_up'] = None
    session['current_idx'] += 1
    session.modified = True
    
    return jsonify({
        "correct": is_correct,
        "answer": q_data['answer'],
        "explanation": q_data['explanation'],
        "score": session['score'],
        "streak": session['streak'],
        "points_gained": (base_points + bonus) if is_correct else 0
    })

@app.route('/use_powerup', methods=['POST'])
def use_powerup():
    pu_name = request.json.get('power_up')
    if pu_name in session.get('power_ups', []):
        session['active_power_up'] = pu_name
        session['power_ups'].remove(pu_name)
        session.modified = True
        return jsonify({"success": True})
    return jsonify({"success": False})

@app.route('/finish')
def finish():
    name = session.get('player_name', 'Guest')
    score = session.get('score', 0)
    duration = round(time.time() - session.get('start_time', time.time()), 2)
    correct = session.get('correct_count', 0)
    total = session.get('total_q', 1)
    acc = (correct / total) * 100
    
    # Attempt to save to leaderboard (optional for Vercel)
    engine.submit_score(name, score, duration, acc)
    
    return render_template('finish.html', name=name, score=score, time=duration, acc=acc, correct=correct, total=total)

@app.route('/api/gemini_study', methods=['POST'])
def gemini_study():
    if not ai_model:
        return jsonify({"summary": "AI module is currently offline. Please check server logs."})
    topic = request.json.get('topic', 'Trigonometri')
    prompt = f"Berikan penjelasan mendalam tentang {topic} untuk siswa SMA. Jelaskan konsep, rumus, dan berikan 1 contoh soal sulit beserta pembahasannya. Gunakan gaya bahasa yang mudah dimengerti."
    try:
        resp = ai_model.generate_content(prompt)
        return jsonify({"summary": resp.text})
    except Exception as e:
        return jsonify({"summary": f"AI Error: {e}"})

@app.route('/scoreboard_data')
def scoreboard_data():
    return jsonify(engine.get_leaderboard())

# --- 5. ADMIN & SECURITY ---
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        u = request.form.get('username')
        p = request.form.get('password')
        if u == ADMIN_USER and check_password_hash(ADMIN_PWD_HASH, p):
            session['admin_active'] = True
            return redirect(url_for('admin_dashboard'))
        return render_template('admin_login.html', error="ACCESS DENIED")
    return render_template('admin_login.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    if not session.get('admin_active'): return redirect(url_for('admin_login'))
    # Load all records
    conn = engine.get_conn(read_only=True)
    rows = conn.execute("SELECT * FROM scoreboard ORDER BY date_played DESC").fetchall()
    conn.close()
    return render_template('admin_dashboard.html', scores=rows)

@app.route('/easter_egg')
def easter_egg():
    return render_template('easter_egg.html', members=GROUP_MEMBERS)

@app.context_processor
def inject_global_data():
    return {
        "school_logo": "/static/img/logo_sman4.jpeg",
        "school_name": "SMAN 4 Jakarta",
        "project_title": "TrigoQuest TIM X-E3"
    }

if __name__ == '__main__':
    # Local production testing
    app.run(host='0.0.0.0', port=5000, debug=False)
