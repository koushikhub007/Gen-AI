import os
from flask import Flask, request, jsonify, render_template
from openai import OpenAI

app = Flask(__name__)

# এখানে তোমার API Key বসাবে। তবে সিকিউরিটির জন্য Environment Variable ভালো।
# লোকাল টেস্টের জন্য সরাসরি বসাতে পারো, কিন্তু Render-এ Environment Variable ব্যবহার করবে।
client = OpenAI(api_key="তোমার_API_KEY_এখানে_বসাও")

@app.route('/')
def home():
    return render_template('index.html') # তোমার HTML ফাইল

@app.route('/chat', methods=['POST'])
def chat():
    # ইউজার যা লিখেছে তা নিচ্ছি
    user_message = request.json.get('message')

    try:
        # OpenAI কে কল করছি (এখানেই ম্যাজিক আছে)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", # এটি সস্তা এবং ফাস্ট
            messages=[
                {"role": "system", "content": "তুমি একজন বাংলা ভাষী স্মার্ট চ্যাটবট। তুমি সবসময় বাংলায় সুন্দর করে উত্তর দাও।"},
                {"role": "user", "content": user_message}
            ]
        )
        
        # AI এর উত্তর বের করছি
        bot_reply = response.choices[0].message.content
        return jsonify({'reply': bot_reply})

    except Exception as e:
        return jsonify({'reply': f"Error: {str(e)}"})

import os

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
