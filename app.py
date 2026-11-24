import sqlite3
from flask import Flask, render_template, request, redirect, session
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'your_secret_key'


# ---------------- AI BASIC FUNCTION ----------------
def get_ai_suggestion(tasks):
    if not tasks:
        return "No tasks yet. Add tasks to get AI suggestions!"

    pending_tasks = [t for t in tasks if not t['completed']]
    completed_tasks = [t for t in tasks if t['completed']]

    if not pending_tasks:
        return "🎉 Excellent! You completed everything!"

    subject_count = {}
    for t in pending_tasks:
        subject = t['task'].split()[0]
        subject_count[subject] = subject_count.get(subject, 0) + 1

    weak_subject = max(subject_count, key=subject_count.get)

    try:
        pending_tasks.sort(
            key=lambda x: datetime.strptime(x['date'], "%Y-%m-%d")
        )
    except:
        return "⚠️ Use correct date format YYYY-MM-DD"

    next_task = pending_tasks[0]
    due_date = datetime.strptime(next_task['date'], "%Y-%m-%d")
    today = datetime.now()

    days_left = (due_date - today).days

    total = len(tasks)
    completed = len(completed_tasks)
    productivity = int((completed / total) * 100)

    msg = f"📚 Next: {next_task['task']} ({days_left} days left)\n"
    msg += f"📉 Weak Subject: {weak_subject}\n"
    msg += f"📊 Productivity: {productivity}%\n"

    return msg


# ---------------- ADVANCED AI ----------------
def advanced_ai(tasks):
    if not tasks:
        return "No data for AI"

    today = datetime.now().date()
    pending = [t for t in tasks if not t['completed']]
    completed = [t for t in tasks if t['completed']]

    for t in pending:
        try:
            d = datetime.strptime(t['date'], "%Y-%m-%d").date()
            if d < today:
                t['date'] = str(today + timedelta(days=1))
        except:
            pass

    score = int((len(completed) / len(tasks)) * 100)

    status = "🔴 Low"
    if score > 75:
        status = "🟢 Ready"
    elif score > 40:
        status = "🟡 Medium"

    msg = f"🎯 Readiness: {score}% ({status})\n"

    return msg


# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task TEXT,
            date TEXT,
            completed INTEGER,
            user_id INTEGER
        )
    ''')

    conn.commit()
    conn.close()


# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('tasks.db')
        c = conn.cursor()

        c.execute("SELECT id FROM users WHERE username=? AND password=?",
                  (username, password))
        user = c.fetchone()
        conn.close()

        if user:
            session['user_id'] = user[0]
            return redirect('/')
        else:
            return "Invalid username or password"

    return render_template('login.html')


# ---------------- SIGNUP ----------------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('tasks.db')
        c = conn.cursor()

        try:
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                      (username, password))
            conn.commit()
        except:
            return "User already exists"

        conn.close()
        return redirect('/login')

    return render_template('signup.html')


# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


# ---------------- HOME ----------------
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()

    c.execute("SELECT id, task, date, completed FROM tasks WHERE user_id=?",
              (session['user_id'],))
    db_tasks = c.fetchall()
    conn.close()

    tasks = []
    for t in db_tasks:
        tasks.append({
            'id': t[0],
            'task': t[1],
            'date': t[2],
            'completed': bool(t[3])
        })

    ai_tip = get_ai_suggestion(tasks)
    final_ai = advanced_ai(tasks)

    return render_template(
        'index.html',
        tasks=tasks,
        ai_tip=ai_tip,
        final_ai=final_ai
    )


# ---------------- ADD TASK ----------------
@app.route('/add', methods=['POST'])
def add():
    if 'user_id' not in session:
        return redirect('/login')

    task = request.form['task']
    date = request.form['date']

    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()

    c.execute("""
        INSERT INTO tasks (task, date, completed, user_id)
        VALUES (?, ?, ?, ?)
    """, (task, date, 0, session['user_id']))

    conn.commit()
    conn.close()

    return redirect('/')


# ---------------- COMPLETE ----------------
@app.route('/complete/<int:task_id>')
def complete(task_id):
    if 'user_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()

    c.execute("UPDATE tasks SET completed=1 WHERE id=? AND user_id=?",
              (task_id, session['user_id']))

    conn.commit()
    conn.close()

    return redirect('/')


# ---------------- DELETE ----------------
@app.route('/delete/<int:task_id>')
def delete(task_id):
    if 'user_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()

    c.execute("DELETE FROM tasks WHERE id=? AND user_id=?",
              (task_id, session['user_id']))

    conn.commit()
    conn.close()

    return redirect('/')


# ---------------- SEARCH ----------------
@app.route('/search', methods=['POST'])
def search():
    if 'user_id' not in session:
        return redirect('/login')

    keyword = request.form['keyword']

    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()

    c.execute("""
        SELECT id, task, date, completed FROM tasks
        WHERE task LIKE ? AND user_id=?
    """, ('%' + keyword + '%', session['user_id']))

    data = c.fetchall()
    conn.close()

    tasks = []
    for t in data:
        tasks.append({
            'id': t[0],
            'task': t[1],
            'date': t[2],
            'completed': bool(t[3])
        })

    ai_tip = get_ai_suggestion(tasks)
    final_ai = advanced_ai(tasks)

    return render_template(
        'index.html',
        tasks=tasks,
        ai_tip=ai_tip,
        final_ai=final_ai
    )


# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM tasks WHERE completed=1 AND user_id=?",
              (session['user_id'],))
    completed = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM tasks WHERE completed=0 AND user_id=?",
              (session['user_id'],))
    pending = c.fetchone()[0]

    c.execute("SELECT date, COUNT(*) FROM tasks WHERE user_id=? GROUP BY date",
              (session['user_id'],))
    data = c.fetchall()

    conn.close()

    dates = [d[0] for d in data]
    counts = [d[1] for d in data]

    return render_template(
        'dashboard.html',
        completed=completed,
        pending=pending,
        dates=dates,
        counts=counts
    )


# ---------------- RUN ----------------
if __name__ == '__main__':
    init_db()
    app.run(debug=True)