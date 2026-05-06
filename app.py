import os
from datetime import datetime
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from openai import OpenAI
import uuid
from urllib.parse import quote_plus

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'my_super_secret_key_123')

# --- MongoDB Setup (Safe Mode) ---
MONGO_USER = os.environ.get("MONGO_USER")
MONGO_PASS = os.environ.get("MONGO_PASS")
MONGO_CLUSTER = os.environ.get("MONGO_CLUSTER")
DB_NAME = "gen_ai_db"

client_db = None
db = None
users_collection = None
history_collection = None

try:
    if MONGO_USER and MONGO_PASS and MONGO_CLUSTER:
        escaped_user = quote_plus(MONGO_USER)
        escaped_pass = quote_plus(MONGO_PASS)
        MONGO_URI = f"mongodb+srv://{escaped_user}:{escaped_pass}@{MONGO_CLUSTER}/{DB_NAME}?retryWrites=true&w=majority"
        
        client_db = MongoClient(MONGO_URI)
        db = client_db[DB_NAME]
        users_collection = db["users"]
        history_collection = db["history"]
        print("MongoDB Connected Successfully!")
    else:
        print("MongoDB credentials missing.")
except Exception as e:
    print(f"MongoDB Connection Error: {e}")

# --- Flask-Login Setup ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_page'

class User(UserMixin):
    def __init__(self, user_doc):
        self.id = str(user_doc['_id'])
        self.username = user_doc['username']

    @staticmethod
    def get(user_id):
        try:
            if users_collection is None: return None
            user_doc = users_collection.find_one({'_id': uuid.UUID(user_id)})
            if user_doc:
                return User(user_doc)
        except:
            pass
        return None

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

# --- Groq Setup (OpenAI Compatible) ---
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ.get("GROQ_API_KEY")
)

# --- Routes ---

@app.route('/')
@login_required
def index():
    return render_template('chat.html', username=current_user.username)

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if users_collection is None:
         return jsonify({'success': False, 'message': 'Database not connected'}), 500

    user_doc = users_collection.find_one({'username': username})
    
    if user_doc and check_password_hash(user_doc['password'], password):
        user_obj = User(user_doc)
        login_user(user_obj)
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'message': 'Invalid username or password'}), 401

@app.route('/api/signup', methods=['POST'])
def api_signup():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'success': False, 'message': 'Missing fields'}), 400

    if users_collection is None:
         return jsonify({'success': False, 'message': 'Database not connected'}), 500
        
    if users_collection.find_one({'username': username}):
        return jsonify({'success': False, 'message': 'User already exists'}), 400
    
    hashed_password = generate_password_hash(password)
    users_collection.insert_one({
        '_id': uuid.uuid4(),
        'username': username,
        'password': hashed_password
    })
    
    return jsonify({'success': True})

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login_page'))

@app.route('/chat', methods=['POST'])
@login_required
def chat():
    data = request.json
    user_message = data.get('message')
    model_type = data.get('model', 'thinking')

    model_mapping = {
        'thinking': 'llama-3.3-70b-versatile',
        'pro': 'llama-3.3-70b-versatile'
    }
    selected_model = model_mapping.get(model_type, 'llama-3.3-70b-versatile')

    if not user_message:
        return jsonify({'reply': "কিছু লিখুন..."})

    try:
        # Groq API Call
        response = client.chat.completions.create(
            model=selected_model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": user_message}
            ]
        )
        
        bot_reply = response.choices[0].message.content

        # Chat History Save
        if history_collection is not None:
            history_collection.insert_one({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "user": current_user.username,
                "message": user_message,
                "bot": bot_reply,
                "model": model_type
            })
        
        return jsonify({'reply': bot_reply})

    except Exception as e:
        return jsonify({'reply': f"Error: {str(e)}"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
