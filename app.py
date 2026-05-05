import os
from flask import Flask, request, jsonify, render_template
from openai import OpenAI

app = Flask(__name__)

# Render থেকে API Key নিচ্ছে
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

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
                    "content": """You are a helpful assistant. 
                    STRICT RULE: You MUST reply in the EXACT SAME language the user uses.
                    - If user writes in English, you MUST reply in English.
                    - If user writes in Bengali, you MUST reply in Bengali.
                    - Do not translate. Do not change the language."""
                },
                {"role": "user", "content": user_message}
            ]
        )
        
        bot_reply = response.choices[0].message.content
        return jsonify({'reply': bot_reply})

        except Exception as e:
        # আগে এখানে শুধু "Sorry" লেখা ছিল, এখন আসল এররটা দেখাবে
        return jsonify({'reply': f"Error: {str(e)}"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
