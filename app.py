import os
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from openai import OpenAI
from pymongo import MongoClient
from urllib.parse import quote_plus

app = Flask(__name__)

# --- MongoDB Setup (Safe Mode) ---
# Password এ বিশেষ অক্ষর থাকলেও সমস্যা হবে না
MONGO_USER = os.environ.get("MONGO_USER")
MONGO_PASS = os.environ.get("MONGO_PASS")
MONGO_CLUSTER = os.environ.get("MONGO_CLUSTER")
DB_NAME = "chatbot_db"

client_db = None
collection = None

try:
    if MONGO_USER and MONGO_PASS and MONGO_CLUSTER:
        escaped_user = quote_plus(MONGO_USER)
        escaped_pass = quote_plus(MONGO_PASS)
        MONGO_URI = f"mongodb+srv://{escaped_user}:{escaped_pass}@{MONGO_CLUSTER}/{DB_NAME}?retryWrites=true&w=majority"
        
        client_db = MongoClient(MONGO_URI)
        db = client_db[DB_NAME]
        collection = db["history"]
        print("MongoDB Connected Successfully!")
    else:
        print("MongoDB credentials missing in environment variables.")
        
except Exception as e:
    print(f"MongoDB Connection Error: {e}")

# --- Groq Setup (OpenAI Compatible) ---
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ.get("GROQ_API_KEY")
)

@app.route('/')
def home():
    # এটি templates ফোল্ডারের index.html খুঁজবে
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message')
    model_type = data.get('model', 'thinking')

    # আপনার পছন্দমতো মডেল সেট করুন
    model_mapping = {
        'thinking': 'llama-3.3-70b-versatile', 
        'pro': 'llama-3.3-70b-versatile'
    }
    selected_model = model_mapping.get(model_type, 'llama-3.3-70b-versatile')

    if not user_message:
        return jsonify({'reply': "কিছু লিখুন..."})

    try:
        response = client.chat.completions.create(
            model=selected_model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": user_message}
            ]
        )
        
        bot_reply = response.choices[0].message.content

        # MongoDB-তে ডাটা সেভ
        if collection is not None:
            try:
                collection.insert_one({
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "user": user_message,
                    "bot": bot_reply,
                    "model": model_type
                })
            except Exception as db_err:
                print(f"DB Insert Error: {db_err}")
        
        return jsonify({'reply': bot_reply})

    except Exception as e:
        return jsonify({'reply': f"API Error: {str(e)}"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
