import os
from flask import Flask, request, jsonify, render_template
import google.generativeai as genai

app = Flask(__name__)

# Gemini API Key সেটআপ
# Render থেকে Environment Variable নিবে
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
        # মডেল কনফিগারেশন (System Instruction সহ)
        # এখানে বলে দেওয়া হলো যেন সে ইউজারের ভাষায় উত্তর দেয়
        model = genai.GenerativeModel(
            model_name='gemini-1.5-flash',
            system_instruction=(
                "You are a helpful and intelligent assistant. "
                "STRICT RULE: You MUST reply in the EXACT SAME language the user uses. "
                "If user writes in English, reply in English. "
                "If user writes in Bengali, reply in Bengali. "
                "Do not translate. Do not change the language."
            )
        )

        # চ্যাট সেশন শুরু
        chat_session = model.start_chat(history=[])
        
        # মেসেজ পাঠানো
        response = chat_session.send_message(user_message)

        bot_reply = response.text
        return jsonify({'reply': bot_reply})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'reply': f"Error: {str(e)}"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
