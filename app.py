import os
import json
import base64
import hashlib
from datetime import datetime
from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from openai import OpenAI
import uuid
from urllib.parse import quote_plus
from cryptography.fernet import Fernet

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'my_super_secret_key_123')

# --- Encryption Setup ---
key_bytes = hashlib.sha256(app.secret_key.encode()).digest()
cipher_key = base64.urlsafe_b64encode(key_bytes)
cipher_suite = Fernet(cipher_key)

def encrypt_data(data):
    if not data: return ""
    json_str = json.dumps(data)
    return cipher_suite.encrypt(json_str.encode()).decode()

def decrypt_data(encrypted_data):
    if not encrypted_data: return []
    try:
        json_str = cipher_suite.decrypt(encrypted_data.encode()).decode()
        return json.loads(json_str)
    except:
        return []

# --- MongoDB Setup ---
MONGO_USER = os.environ.get("MONGO_USER")
MONGO_PASS = os.environ.get("MONGO_PASS")
MONGO_CLUSTER = os.environ.get("MONGO_CLUSTER")
DB_NAME = "gen_ai_db"

client_db = None
db = None
users_collection = None

try:
    if MONGO_USER and MONGO_PASS and MONGO_CLUSTER:
        escaped_user = quote_plus(MONGO_USER)
        escaped_pass = quote_plus(MONGO_PASS)
        MONGO_URI = f"mongodb+srv://{escaped_user}:{escaped_pass}@{MONGO_CLUSTER}/{DB_NAME}?retryWrites=true&w=majority"
        
        client_db = MongoClient(MONGO_URI)
        db = client_db[DB_NAME]
        users_collection = db["users"]
        print("MongoDB Connected Successfully!")
except Exception as e:
    print(f"MongoDB Connection Error: {e}")

# --- API Clients Setup ---
zhipu_client = None
groq_client = None

zhipu_key = os.environ.get("ZHIPU_API_KEY")
groq_key = os.environ.get("GROQ_API_KEY")

if zhipu_key:
    zhipu_client = OpenAI(
        api_key=zhipu_key,
        base_url="https://open.bigmodel.cn/api/paas/v4/"
    )
    print("Zhipu AI Ready")

if groq_key:
    groq_client = OpenAI(
        api_key=groq_key,
        base_url="https://api.groq.com/openai/v1"
    )
    print("Groq AI Ready")

# --- Login Manager & Routes (Signup/Login/Logout same as before) ---
# ... (সংক্ষেপের জন্য আগের কোডের লজিক একই থাকবে, নিচে শুধু চ্যাট রুটটি দেওয়া হলো)

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
        login_user(u, remember=True)
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Invalid username or password'}), 401

@app.route('/api/signup', methods=['POST'])
def api_signup():
    data = request.json
    if users_collection is None: return jsonify({'success': False, 'message': 'Database Error'}), 500
    username = data.get('username')
    password = data.get('password')
    if not username or not password: return jsonify({'success': False, 'message': 'Missing fields'}), 400
    if users_collection.find_one({'username': username}): return jsonify({'success': False, 'message': 'User already exists'}), 400
    user_id = str(uuid.uuid4())
    users_collection.insert_one({'_id': user_id, 'username': username, 'password': generate_password_hash(password), 'encrypted_history': ""})
    return jsonify({'success': True})

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login_page'))

# --- Chat Route (Corrected Model IDs) ---

@app.route('/chat', methods=['POST'])
@login_required
def chat():
    data = request.json
    user_text = data.get('message')
    model_key = data.get('model', 'glm-4-flash') # ডিফল্ট glm-4-flash

    # মডেল সিলেকশন লজিক
    client = None
    model_id = None

    if model_key == 'glm-4-flash':
        if not zhipu_client: return jsonify({'reply': "Zhipu API Key missing"})
        client = zhipu_client
        model_id = "glm-4-flash" # ডকুমেন্টেশন অনুযায়ী সঠিক নাম
        
    elif model_key == 'glm-4-air':
        if not zhipu_client: return jsonify({'reply': "Zhipu API Key missing"})
        client = zhipu_client
        model_id = "glm-4-air" # ডকুমেন্টেশন অনুযায়ী সঠিক নাম
        
    elif model_key == 'llama-70b':
        if not groq_client: return jsonify({'reply': "Groq API Key missing"})
        client = groq_client
        model_id = "llama-3.3-70b-versatile"
        
    elif model_key == 'llama-8b':
        if not groq_client: return jsonify({'reply': "Groq API Key missing"})
        client = groq_client
        model_id = "llama-3.1-8b-instant"
        
    else:
        return jsonify({'reply': "Invalid Model Selection"})

    try:
        response = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": user_text}]
        )
        bot_reply = response.choices[0].message.content
        return jsonify({'reply': bot_reply})
    except Exception as e:
        return jsonify({'reply': f"Error: {str(e)}"})

# History Routes...
@app.route('/api/save_history', methods=['POST'])
@login_required
def save_history():
    data = request.json
    history_list = data.get('history', [])
    encrypted_string = encrypt_data(history_list)
    users_collection.update_one({'username': current_user.username}, {'$set': {'encrypted_history': encrypted_string}})
    return jsonify({'success': True})

@app.route('/api/get_history')
@login_required
def get_history():
    user_doc = users_collection.find_one({'username': current_user.username})
    if user_doc and 'encrypted_history' in user_doc:
        decrypted_list = decrypt_data(user_doc['encrypted_history'])
        return jsonify({'history': decrypted_list})
    return jsonify({'history': []})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
