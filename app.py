import os
from flask import Flask, request, jsonify, render_template
from openai import OpenAI

app = Flask(__name__)

# Groq API Setup (OpenAI SDK ব্যবহার করে)
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ.get("GROQ_API_KEY")
)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message')
    
    if not user_message:
        return jsonify({'reply': "কিছু লিখুন..."})

    try:
        # Groq এর জন্য মডেল: llama3-8b-8192 (এটি ফ্রি এবং দ্রুত)
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a helpful assistant. You MUST reply in the EXACT SAME language the user uses. If user types in Bengali, reply in Bengali. If English, reply in English."
                },
                {"role": "user", "content": user_message}
            ]
        )
        
        bot_reply = response.choices[0].message.content
        return jsonify({'reply': bot_reply})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'reply': f"Error: {str(e)}"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
