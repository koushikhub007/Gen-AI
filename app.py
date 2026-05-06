import os
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from openai import OpenAI
from pymongo import MongoClient

app = Flask(__name__)

# --- MongoDB Setup ---
MONGO_URI = os.environ.get("MONGO_URI")
try:
    client_db = MongoClient(MONGO_URI)
    db = client_db["chatbot_db"]
    collection = db["history"]
    print("MongoDB Connected!")
except Exception as e:
    print(f"MongoDB Error: {e}")

# --- Groq Setup ---
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ.get("GROQ_API_KEY")
)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message')
    model_type = data.get('model', 'fast') # UI থেকে কোন মডেল এসেছে

    # UI এর নাম অনুযায়ী আসল মডেল সিলেক্ট করা
    model_mapping = {
        'fast': 'llama-3.1-8b-instant',
        'thinking': 'llama-3.3-70b-versatile',
        'pro': 'llama-3.3-70b-versatile'
    }
    selected_model = model_mapping.get(model_type, 'llama-3.1-8b-instant')

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

        # MongoDB তে সেভ করা
        if 'collection' in globals():
            collection.insert_one({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "user": user_message,
                "bot": bot_reply,
                "model": model_type
            })
        
        return jsonify({'reply': bot_reply})

    except Exception as e:
        return jsonify({'reply': f"Error: {str(e)}"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
