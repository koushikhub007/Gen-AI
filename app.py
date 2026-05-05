import os
from flask import Flask, request, jsonify, render_template
from openai import OpenAI

app = Flask(__name__)

# ১. এখানে Environment Variable থেকে Key নিচ্ছি। 
# Render-এ গিয়ে Environment Variable নাম দিয়ে 'OPENAI_API_KEY' এবং Value তে তোমার Key দিতে হবে।
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# ২. হোম পেজের জন্য Route
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message')

    try:
        # OpenAI API Call
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a helpful and intelligent assistant. You must detect the language of the user's input and reply in the EXACT SAME language. If the user types in Bengali, reply in Bengali. If English, reply in English. Maintain the tone and language of the user."
                },
                {"role": "user", "content": user_message}
            ]
        )
        
        # AI এর উত্তর বের করছি
        bot_reply = response.choices[0].message.content
        return jsonify({'reply': bot_reply})

    except Exception as e:
        # এরর হলে কনসোলে দেখাবে
        print(f"Error: {e}")
        return jsonify({'reply': "দুঃখিত, আমি এই মুহূর্তে উত্তর দিতে পারছি না।"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
