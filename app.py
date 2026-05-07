import os
from datetime import datetime
from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from openai import OpenAI
import uuid
from urllib.parse import quote_plus

app = Flask(__name__)
# SECRET_KEY অবশ্যই Environment Variable এ দিতে হবে, না হলে রিস্টার্ট দিলে সেশন চলে যাবে
app.secret_key = os.environ.get('SECRET_KEY', 'my_super_secret_key_123')

# --- MongoDB Setup ---
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
        # History সেভ করার জন্য আলাদা collection
        history_collection = db["user_histories"] 
        print("MongoDB Connected Successfully!")
except Exception as e:
    print(f"MongoDB Connection Error: {e}")

# --- Groq Setup ---
groq_key = os.environ.get("GROQ_API_KEY")
client = None
if groq_key:
    client = OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=groq_key
    )

# --- Login Manager ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_page'

class User(UserMixin):
    def __init__(self, user_doc):
        self.id = str(user_doc['_id'])
        self.username = user_doc['username']

    @staticmethod
    def get(user_id):
        if users_collection is None: return None
        user_doc = users_collection.find_one({'_id': user_id})
        return User(user_doc) if user_doc else None

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

# --- Routes ---

@app.route('/')
@login_required
def index():
    return render_template('index.html', username=current_user.username)

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    if users_collection is None: return jsonify({'success': False, 'message': 'Database Error'}), 500
    
    user_doc = users_collection.find_one({'username': data.get('username')})
    if user_doc and check_password_hash(user_doc['password'], data.get('password')):
        u = User(user_doc)
        # 'remember=True' দিলে ব্রাউজার বন্ধ করলেও লগইন থাকবে
        login_user(u, remember=True) 
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Invalid username or password'}), 401

@app.route('/api/signup', methods=['POST'])
def api_signup():
    data = request.json
    if users_collection is None: return jsonify({'success': False, 'message': 'Database Error'}), 500
    
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'success': False, 'message': 'Missing fields'}), 400
        
    if users_collection.find_one({'username': username}):
        return jsonify({'success': False, 'message': 'User already exists'}), 400
    
    user_id = str(uuid.uuid4())
    users_collection.insert_one({
        '_id': user_id,
        'username': username,
        'password': generate_password_hash(password)
    })
    return jsonify({'success': True})

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login_page'))

# --- Chat & History Routes ---

@app.route('/chat', methods=['POST'])
@login_required
def chat():
    if client is None:
        return jsonify({'reply': "AI Service not configured."})

    data = request.json
    user_text = data.get('message')
    
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": user_text}]
        )
        bot_reply = response.choices[0].message.content

        # ১. Message ডাটাবেসে সেভ করা হচ্ছে (ঐচ্ছিক, তবে ভবিষ্যতের জন্য ভালো)
        # ২. এখানে আমরা History Sync API এর জন্য শুধু Chat করব, History Frontend থেকে আলাদাভাবে সেভ হবে
        
        return jsonify({'reply': bot_reply})
    except Exception as e:
        return jsonify({'reply': f"Error: {str(e)}"})

# History সেভ করার API
@app.route('/api/save_history', methods=['POST'])
@login_required
def save_history():
    data = request.json
    # User ভিত্তিক History আপডেট করা
    users_collection.update_one(
        {'username': current_user.username},
        {'$set': {'chat_history': data.get('history', [])}}
    )
    return jsonify({'success': True})

# History লোড করার API
@app.route('/api/get_history')
@login_required
def get_history():
    user_doc = users_collection.find_one({'username': current_user.username})
    if user_doc and 'chat_history' in user_doc:
        return jsonify({'history': user_doc['chat_history']})
    return jsonify({'history': []})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
