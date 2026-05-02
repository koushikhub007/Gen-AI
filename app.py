import gradio as gr
from groq import Groq
import edge_tts
import asyncio
import os
import uuid

# এখানে আপনার API Key থাকবে (নিচে বলে দেব কোথায় দেবেন)
client = Groq(api_key=os.environ.get("GROQ_KEY"))

async def generate_voice(text):
    filename = f"response_{uuid.uuid4()}.mp3"
    communicate = edge_tts.Communicate(text, "bn-IN-TanishaaNeural", rate="-10%")
    await communicate.save(filename)
    return filename

def assistant(audio_file, text_input):
    user_text = ""
    
    if audio_file:
        try:
            with open(audio_file, "rb") as file:
                transcription = client.audio.transcriptions.create(
                    file=(audio_file, file.read()),
                    model="whisper-large-v3-turbo",
                    language="bn",
                    response_format="text"
                )
            user_text = transcription
        except Exception as e:
            return f"ভয়েস ইরর: {e}", None
            
    elif text_input:
        user_text = text_input
        
    if not user_text:
        return "বুঝতে পারছি না।", None

    try:
        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": user_text}],
            model="llama-3.1-8b-instant",
        )
        reply = completion.choices[0].message.content
    except Exception as e:
        return f"AI ইরর: {e}", None

    try:
        voice_path = asyncio.run(generate_voice(reply))
        return reply, voice_path
    except Exception as e:
        return f"ভয়েস ইরর: {e}", None

demo = gr.Interface(
    fn=assistant,
    inputs=[
        gr.Audio(sources=["microphone"], type="filepath", label="🎤 কথা বলুন"),
        gr.Textbox(label="✍️ লিখুন")
    ],
    outputs=[
        gr.Textbox(label="📝 উত্তর"),
        gr.Audio(label="🔊 ভয়েস", autoplay=True)
    ],
    title="🤖 জার্ভিস"
)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)