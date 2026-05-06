import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from openai import OpenAI
import uuid
# নতুন লাইন যোগ করুন
from urllib.parse import quote_plus

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your_default_secret_key_here')

# --- Database Setup (MongoDB) ---
# আলাদা আলাদা Environment Variable নিন
MONGO_USER = os.environ.get('MONGO_USER')
MONGO_PASS = os.environ.get('MONGO_PASS')
MONGO_CLUSTER = os.environ.get('MONGO_CLUSTER') # যেমন: cluster0.abcde.mongodb.net

# Password এবং Username Encode করুন
if MONGO_USER and MONGO_PASS and MONGO_CLUSTER:
    escaped_user = quote_plus(MONGO_USER)
    escaped_pass = quote_plus(MONGO_PASS)
    MONGO_URI = f"mongodb+srv://{escaped_user}:{escaped_pass}@{MONGO_CLUSTER}/?retryWrites=true&w=majority"
else:
    # Local testing এর জন্য fallback
    MONGO_URI = 'mongodb://localhost:27017/gen_ai_db'

client = MongoClient(MONGO_URI)
db = client.get_database()
users_collection = db.users

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
            user_doc = users_collection.find_one({'_id': uuid.UUID(user_id)})
            if user_doc:
                return User(user_doc)
        except:
            pass
        return None

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

# --- OpenAI Setup ---
# Ensure you set the OPENAI_API_KEY environment variable in Render
openai_client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

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
    model_id = data.get('model', 'thinking') # 'thinking' or 'pro'

    if not user_message:
        return jsonify({'reply': 'Empty message received.'})

    try:
        # Select model based on input
        # Note: Adjust model names as per your OpenAI subscription
        model_name = "gpt-3.5-turbo" if model_id == 'pro' else "gpt-4o-mini" 
        
        response = openai_client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": user_message}]
        )
        reply = response.choices[0].message.content
        return jsonify({'reply': reply})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'reply': f"An error occurred: {str(e)}"})

if __name__ == '__main__':
    # Render sets the PORT environment variable
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
