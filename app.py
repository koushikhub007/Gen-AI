import os
from datetime import datetime
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from openai import OpenAI
from pymongo import MongoClient
from bson.objectid import ObjectId

app = Flask(__name__)
app.secret_key = os.urandom(24)

# --- MongoDB Setup ---
MONGO_URI = os.environ.get("MONGO_URI")
client_db = MongoClient(MONGO_URI)
db = client_db["gen_ai_db"]
users_col = db["users"]
chats_col = db["chats"]

# --- Flask-Login Setup ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_page'

class User(UserMixin):
    def __init__(self, user_doc):
        self.id = str(user_doc['_id'])
        self.username = user_doc['username']

@login_manager.user_loader
def load_user(user_id):
    user_doc = users_col.find_one({"_id": ObjectId(user_id)})
    if user_doc:
        return User(user_doc)
    return None

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
    username = data.get('username')
    password = data.get('password')
    
    user = users_col.find_one({"username": username})
    if user and check_password_hash(user['password'], password):
        user_obj = User(user)
        login_user(user_obj)
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Invalid username or password"})

@app.route('/api/signup', methods=['POST'])
def api_signup():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if users_col.find_one({"username": username}):
        return jsonify({"success": False, "message": "Username already exists"})
    
    hashed_pw = generate_password_hash(password)
    users_col.insert_one({"username": username, "password": hashed_pw})
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
    user_message = data.get('message')
    model_type = data.get('model', 'thinking')

    model_mapping = {
        'thinking': 'llama-3.3-70b-versatile',
        'pro': 'llama-3.3-70b-versatile'
    }
    selected_model = model_mapping.get(model_type, 'llama-3.3-70b-versatile')

    try:
        response = client.chat.completions.create(
            model=selected_model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": user_message}
            ]
        )
        
        bot_reply = response.choices[0].message.content

        # Save to Database
        chats_col.insert_one({
            "user_id": current_user.id,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user_message": user_message,
            "bot_reply": bot_reply
        })
        
        return jsonify({'reply': bot_reply})

    except Exception as e:
        return jsonify({'reply': f"Error: {str(e)}"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
