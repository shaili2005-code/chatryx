from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import google.generativeai as genai
from PyPDF2 import PdfReader
from dotenv import load_dotenv
import redis
import psycopg2
import psycopg2.extras
import time
import uuid

app = Flask(__name__)
CORS(app)

load_dotenv()

app.secret_key = os.getenv("SECRET_KEY", "super-secret-key")

REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))

POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
POSTGRES_DB = os.getenv('POSTGRES_DB', 'mydatabase')
POSTGRES_USER = os.getenv('POSTGRES_USER', 'myuser')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'mypassword')

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY not set in environment variables")

genai.configure(api_key=GEMINI_API_KEY)
default_model = "models/gemini-2.5-flash"

redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

max_attempts = 10
for attempt in range(max_attempts):
    try:
        conn = psycopg2.connect(
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            host=POSTGRES_HOST,
            port=5432
        )
        conn.autocommit = True
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        print("Connected to Postgres")
        break
    except psycopg2.OperationalError as e:
        print(f"Postgres connection failed (attempt {attempt + 1}/{max_attempts}): {e}")
        time.sleep(3)
else:
    raise RuntimeError("Could not connect to Postgres after several attempts.")

app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

PDF_CACHE_KEY = "pdf_text_cache"

def create_tables():
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id UUID PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            chat_session_id UUID REFERENCES chat_sessions(id),
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

create_tables()

def create_new_chat_session():
    new_session_id = str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO chat_sessions (id, user_id) VALUES (%s, %s)",
        (new_session_id, session['user_id'])
    )
    session['chat_session_id'] = new_session_id
    return new_session_id

@app.before_request
def ensure_chat_session():
    if 'user_id' in session:
        if 'chat_session_id' not in session:
            create_new_chat_session()

def load_pdf_text(path):
    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages[:3])

def get_answer(query, model_name, pdf_text=None):
    model = genai.GenerativeModel(model_name=model_name)
    if pdf_text:
        prompt = f"""
You are a precise and helpful assistant. Use the following PDF content to answer the user's question **briefly and accurately**.

PDF Content:
{pdf_text}

Question: "{query}"

If the answer is clearly found in the PDF, respond with that information.
If not, answer generally using your own knowledge.

Limit your answer to 3-5 sentences. Do not make up information not supported by the PDF or general facts.

Answer:
"""
    else:
        prompt = f"""
You are a helpful assistant. Answer the following question **accurately and concisely** in 3-5 sentences.

Question: "{query}"

Answer:
"""
    response = model.generate_content(prompt)
    return response.text.strip()

def is_meaningful_answer(text):
    if not text:
        return False
    text = text.strip().lower()
    fallback_phrases = [
        "i don't know",
        "do not know",
        "sorry",
        "not sure",
        "no answer",
        "unable to",
        "cannot find",
        "couldn't find",
        "can't answer"
    ]
    return not any(phrase in text for phrase in fallback_phrases)

# ---------- New API: Get all chat sessions for logged-in user -----------

@app.route("/api/chat_sessions")
def get_chat_sessions():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    cursor.execute("""
        SELECT id, created_at
        FROM chat_sessions
        WHERE user_id = %s
        ORDER BY created_at DESC
    """, (session['user_id'],))
    sessions = cursor.fetchall()
    result = []
    for s in sessions:
        result.append({
            "id": s["id"],
            "name": s["created_at"].strftime("%Y-%m-%d %H:%M:%S")
        })
    return jsonify(result)

@app.route("/")
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template("index.html", username=session.get('username'))

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form['username'].strip()
        password = request.form['password']

        if not username or not password:
            flash("Yo! Username and password can’t be empty.")
            return redirect(url_for('signup'))

        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            flash("That username's already taken. Try another.")
            return redirect(url_for('signup'))

        pw_hash = generate_password_hash(password)
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", (username, pw_hash))
        flash("You’re all set! Now log in and ride the wave 🌊")
        return redirect(url_for('login'))

    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form['username'].strip()
        password = request.form['password']

        cursor.execute("SELECT id, password_hash FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = username
            create_new_chat_session()
            flash(f"Welcome back, {username}! Let’s get chatting.")
            return redirect(url_for('index'))
        else:
            flash("Oops! Wrong username or secret stash.")
            return redirect(url_for('login'))

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Catch you later! You’ve been logged out.")
    return redirect(url_for('login'))

@app.route("/api/upload", methods=["POST"])
def upload():
    if 'user_id' not in session:
        return jsonify({"error": "You gotta log in first!"}), 401

    if 'pdf' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['pdf']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    pdf_text = load_pdf_text(filepath)
    redis_client.set(PDF_CACHE_KEY, pdf_text)
    return jsonify({"message": "PDF uploaded and processed."})

@app.route("/api/ask", methods=["POST"])
def ask():
    if 'user_id' not in session:
        return jsonify({"error": "You gotta log in to chat!"}), 401

    data = request.get_json()
    question = data.get("question")
    model = data.get("model", default_model)
    use_pdf = data.get("use_pdf", False)
    chat_session_id = data.get("chat_session_id") or session.get('chat_session_id')

    if not question:
        return jsonify({"error": "Question is required."}), 400

    try:
        pdf_text_cache = None
        if use_pdf:
            pdf_text_cache = redis_client.get(PDF_CACHE_KEY)
            if pdf_text_cache:
                pdf_text_cache = pdf_text_cache.decode('utf-8')

        final_answer = None
        if use_pdf and pdf_text_cache:
            answer_pdf = get_answer(question, model, pdf_text_cache)
            if is_meaningful_answer(answer_pdf):
                final_answer = answer_pdf
            else:
                final_answer = get_answer(question, model, None)
        else:
            final_answer = get_answer(question, model, None)

        # Save chat history
        cursor.execute(
            "INSERT INTO chat_history (user_id, chat_session_id, question, answer) VALUES (%s, %s, %s, %s)",
            (session['user_id'], chat_session_id, question, final_answer)
        )
        # Update session chat_session_id if new
        session['chat_session_id'] = chat_session_id

        return jsonify({"answer": final_answer})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/history", methods=["GET"])
def history():
    if 'user_id' not in session:
        return jsonify({"error": "You gotta log in to see your history!"}), 401
    chat_session_id = request.args.get("session_id") or session.get('chat_session_id')
    if not chat_session_id:
        return jsonify([])

    try:
        cursor.execute("""
            SELECT question, answer
            FROM chat_history
            WHERE user_id = %s AND chat_session_id = %s
            ORDER BY id ASC
        """, (session['user_id'], chat_session_id))
        rows = cursor.fetchall()
        history_list = []
        for row in rows:
            history_list.append({"sender": "user", "message": row["question"]})
            history_list.append({"sender": "ai", "message": row["answer"]})
        return jsonify(history_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/new_chat", methods=["POST"])
def new_chat():
    if 'user_id' not in session:
        return jsonify({"error": "You gotta log in to start a new chat!"}), 401
    try:
        new_session_id = create_new_chat_session()
        redis_client.delete(PDF_CACHE_KEY)
        return jsonify({"message": "Started a fresh chat session!", "chat_session_id": new_session_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # app.run(debug=True, host="0.0.0.0", port=5000)
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
