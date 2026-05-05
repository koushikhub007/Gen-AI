import os
from flask import Flask, request, jsonify, render_template
import google.generativeai as genai

app = Flask(__name__)

# API Key সেটআপ
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message')
    if not user_message:
        return jsonify({'reply': "কিছু লিখুন..."})

    try:
        # মডেল সেটআপ - এখানে নাম পরিবর্তন করা হয়েছে
        model = genai.GenerativeModel(
            'gemini-1.5-flash-latest',
            system_instruction=(
                "You are a helpful assistant. "
                "Reply in the same language the user uses. "
                "If Bengali, reply in Bengali. If English, reply in English."
            )
        )
        
        # রেসপন্স তৈরি
        response = model.generate_content(user_message)
        
        return jsonify({'reply': response.text})

    except Exception as e:
        # স্পেসিফিক এরর মেসেজ দেখাবে
        return jsonify({'reply': f"Error: {str(e)}"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
