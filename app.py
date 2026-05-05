import os
from flask import Flask, request, jsonify, render_template
from google import genai
from google.genai import types

app = Flask(__name__)

# Gemini Client তৈরি
client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message')
    
    if not user_message:
        return jsonify({'reply': "কিছু লিখুন..."})

    try:
        # নতুন API কল (মডেলের নাম ঠিক করা হয়েছে)
        response = client.models.generate_content(
            model="gemini-1.5-flash-latest", 
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=(
                    "You are a helpful assistant. "
                    "You MUST reply in the EXACT SAME language the user uses. "
                    "If user writes in Bengali, reply in Bengali. "
                    "If user writes in English, reply in English."
                )
            )
        )

        bot_reply = response.text
        return jsonify({'reply': bot_reply})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'reply': f"Error: {str(e)}"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
