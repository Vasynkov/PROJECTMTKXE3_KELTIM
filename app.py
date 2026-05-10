import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import sqlite3
import random
import time

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'cryesix_secret_123')

# Use absolute path for SQLite DB
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, os.getenv('DATABASE_URL', 'trigonometri.db'))

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/learn')
def learn():
    return render_template('learn.html')

@app.route('/api/ai_summary', methods=['POST'])
def ai_summary():
    summary = (
        "Trigonometri Kuadran dan Sudut Istimewa:\n"
        "1. Kuadran I (0-90°): Semua fungsi (sin, cos, tan) bernilai POSITIF.\n"
        "2. Kuadran II (90-180°): Hanya SIN yang POSITIF. Gunakan (180-α).\n"
        "3. Kuadran III (180-270°): Hanya TAN yang POSITIF. Gunakan (180+α).\n"
        "4. Kuadran IV (270-360°): Hanya COS yang POSITIF. Gunakan (360-α).\n"
        "Tips: Ingat 'Semua Sindikat Tangannya Kosong'!"
    )
    return jsonify({"summary": summary})

@app.route('/start_game', methods=['POST'])
def start_game():
    name = request.form.get('player_name')
    if not name:
        name = "Guest Player"
    
    session['player_name'] = name
    session['score'] = 0
    session['start_time'] = time.time()
    session['streak'] = 0
    session['power_ups'] = ['Double Points', 'Eraser', 'Shield']
    session['active_power_up'] = None
    
    try:
        db = get_db()
        all_q = db.execute('SELECT id FROM questions').fetchall()
        db.close()
        
        if len(all_q) < 20:
            # If not enough questions, use what we have
            q_count = len(all_q)
            selected_indices = random.sample(range(q_count), q_count)
            session['total_questions'] = q_count
        else:
            selected_indices = random.sample(range(len(all_q)), 20)
            session['total_questions'] = 20
            
        session['question_indices'] = [all_q[i]['id'] for i in selected_indices]
        session['current_q_idx'] = 0
        session['correct_count'] = 0
        
        return redirect(url_for('game'))
    except Exception as e:
        print(f"Error starting game: {e}")
        return f"Internal Server Error: {e}", 500

@app.route('/game')
def game():
    if 'question_indices' not in session:
        return redirect(url_for('home'))
    
    idx = session['current_q_idx']
    total = session.get('total_questions', 20)
    
    if idx >= total:
        return redirect(url_for('finish'))
    
    q_id = session['question_indices'][idx]
    db = get_db()
    question = db.execute('SELECT * FROM questions WHERE id = ?', (q_id,)).fetchone()
    db.close()
    
    if not question:
        return "Question not found", 404
    
    return render_template('game.html', 
                           question=dict(question), 
                           q_num=idx+1, 
                           total_q=total,
                           power_ups=session.get('power_ups', []),
                           streak=session.get('streak', 0),
                           score=session.get('score', 0))

@app.route('/use_powerup', methods=['POST'])
def use_powerup():
    power_up = request.json.get('power_up')
    if power_up in session.get('power_ups', []):
        session['active_power_up'] = power_up
        session['power_ups'].remove(power_up)
        session.modified = True
        return jsonify({"success": True, "message": f"{power_up} Activated!"})
    return jsonify({"success": False, "message": "Power-up not available"})

@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    user_answer = request.form.get('answer')
    q_id = request.form.get('q_id')
    
    db = get_db()
    q = db.execute('SELECT * FROM questions WHERE id = ?', (q_id,)).fetchone()
    db.close()
    
    is_correct = (user_answer == q['answer'])
    
    points = 10
    bonus = 0
    
    active_pu = session.get('active_power_up')
    
    if is_correct:
        session['streak'] += 1
        session['correct_count'] += 1
        
        # Streak bonus
        if session['streak'] >= 3:
            bonus += 5
        
        # Power-up effect
        if active_pu == 'Double Points':
            points *= 2
            
        session['score'] += (points + bonus)
    else:
        if active_pu == 'Shield':
            # Shield prevents score loss or just counts as wrong but no streak reset?
            # Let's say Shield keeps the streak alive once.
            pass
        else:
            session['streak'] = 0
            
    session['active_power_up'] = None # Clear active power-up
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

@app.route('/finish')
def finish():
    player_name = session.get('player_name', 'Guest')
    score = session.get('score', 0)
    end_time = time.time()
    start_time = session.get('start_time', end_time)
    time_taken = round(end_time - start_time, 2)
    
    total = session.get('total_questions', 20)
    correct = session.get('correct_count', 0)
    accuracy = (correct / total) * 100 if total > 0 else 0
    
    # Save to scoreboard
    try:
        db = get_db()
        db.execute('INSERT INTO scoreboard (name, score, time_taken, accuracy) VALUES (?, ?, ?, ?)',
                   (player_name, score, time_taken, accuracy))
        db.commit()
        db.close()
    except Exception as e:
        print(f"Error saving to scoreboard: {e}")
        # On Vercel this might fail due to read-only DB, but we continue
    
    return render_template('finish.html', 
                           name=player_name, 
                           score=score, 
                           time=time_taken, 
                           acc=accuracy,
                           correct=correct,
                           total=total)

@app.route('/scoreboard_data')
def scoreboard_data():
    try:
        db = get_db()
        scores = db.execute('SELECT * FROM scoreboard ORDER BY score DESC, time_taken ASC LIMIT 10').fetchall()
        db.close()
        return jsonify([dict(row) for row in scores])
    except:
        return jsonify([])

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        usn = request.form.get('username')
        pwd = request.form.get('password')
        admin_usn = os.getenv('ADMIN_USERNAME', 'admin')
        admin_pwd = os.getenv('ADMIN_PASSWORD', 'password')
        if usn == admin_usn and pwd == admin_pwd:
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return "Akses Ditolak!", 403
    return render_template('admin_login.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    db = get_db()
    scores = db.execute('SELECT * FROM scoreboard ORDER BY date_played DESC').fetchall()
    db.close()
    return render_template('admin_dashboard.html', scores=scores)

@app.route('/easter_egg')
def easter_egg():
    gilang_info = {
        "name": "Gilang Satria Pratama",
        "username": "cryesix_",
        "role": "Lead Programmer & UI/UX Designer",
        "bio": "Seorang murid SMAN 4 Jakarta yang memiliki passion tinggi dalam pemrograman dan desain. Dikenal dengan kepribadian yang kreatif, tekun, dan menyukai tantangan teknologi.",
        "ig_link": "https://www.instagram.com/cryesix_/",
        "photo_url": "/static/img/gilang_placeholder.jpg"
    }
    return render_template('easter_egg.html', info=gilang_info)

@app.context_processor
def inject_school_info():
    return {
        "school_logo": "/static/img/logo_sman4.jpeg",
        "school_name": "SMAN 4 Jakarta",
        "school_loc": "Jl. Batu III No. 3, Gambir, Jakarta Pusat",
        "project_title": "TrigoQuest Quizizz Edition"
    }

if __name__ == '__main__':
    app.run(debug=True, port=5000)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
