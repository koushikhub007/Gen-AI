import os
import urllib.parse
from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from openai import OpenAI
from pymongo import MongoClient
from bson.objectid import ObjectId

app = Flask(__name__)
app.secret_key = os.urandom(24)

# --- Database Connection (Auto Fix Magic) ---
MONGO_URI = os.environ.get("MONGO_URI")

if MONGO_URI:
    try:
        # URI থেকে ইউজার এবং পাসওয়ার্ড আলাদা করছি
        parsed = urllib.parse.urlparse(MONGO_URI)
        username = urllib.parse.quote_plus(parsed.username)
        password = urllib.parse.quote_plus(parsed.password)
        host = parsed.hostname
        
        # ঠিক করা নতুন URI তৈরি করছি
        safe_uri = f"{parsed.scheme}://{username}:{password}@{host}{parsed.path}?retryWrites=true&w=majority"
        
        client_db = MongoClient(safe_uri)
        print("Database Connected Successfully!")
    except Exception as e:
        print("Database Connection Error:", e)
        client_db = None
else:
    print("MONGO_URI not found!")
    client_db = None

db = client_db["gen_ai_db"]
users_col = db["users"]
chats_col = db["chats"]

# --- Login Setup ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_page'

class User(UserMixin):
    def __init__(self, user_doc):
        self.id = str(user_doc['_id'])
        self.username = user_doc['username']

@login_manager.user_loader
def load_user(user_id):
    if not client_db: return None
    user_doc = users_col.find_one({"_id": ObjectId(user_id)})
    return User(user_doc) if user_doc else None

# --- Groq Setup ---
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ.get("GROQ_API_KEY")
)

# --- Routes ---

@app.route('/')
def index():
    if current_user.is_authenticated:
        return render_template('chat.html', username=current_user.username)
    return redirect(url_for('login_page'))

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    user = users_col.find_one({"username": data.get('username')})
    if user and check_password_hash(user['password'], data.get('password')):
        login_user(User(user))
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Invalid credentials"})

@app.route('/api/signup', methods=['POST'])
def api_signup():
    data = request.json
    if users_col.find_one({"username": data.get('username')}):
        return jsonify({"success": False, "message": "User exists"})
    hashed_pw = generate_password_hash(data.get('password'))
    users_col.insert_one({"username": data.get('username'), "password": hashed_pw})
    return jsonify({"success": True})

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login_page'))

@app.route('/chat', methods=['POST'])
@login_required
def chat():
    data = request.json
    model_map = {'thinking': 'llama-3.3-70b-versatile', 'pro': 'llama-3.3-70b-versatile'}
    try:
        res = client.chat.completions.create(
            model=model_map.get(data.get('model'), 'llama-3.3-70b-versatile'),
            messages=[{"role": "user", "content": data.get('message')}]
        )
        reply = res.choices[0].message.content
        chats_col.insert_one({"user_id": current_user.id, "msg": data.get('message'), "reply": reply})
        return jsonify({'reply': reply})
    except Exception as e:
        return jsonify({'reply': f"Error: {str(e)}"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
