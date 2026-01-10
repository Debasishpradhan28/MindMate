import streamlit as st
import google.generativeai as genai
import pandas as pd
from datetime import datetime
import time
from gtts import gTTS
import speech_recognition as sr
from streamlit_mic_recorder import mic_recorder
import os

st.set_page_config(
    page_title="MindMate Ultimate",
    page_icon="🧠",
    layout="wide"
)

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "I'm here. How are you feeling?"}]
if "mood_log" not in st.session_state:
    st.session_state.mood_log = [{"Time": datetime.now().strftime("%H:%M:%S"), "Label": "Neutral", "Score": 5}]

try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except FileNotFoundError:
    st.warning("⚠️ Secrets not found. Please set up .streamlit/secrets.toml")
    st.stop()

try:
    if "PASTE_YOUR_KEY" in GOOGLE_API_KEY:
        st.error("🚨 STOP: Paste your API Key in line 26!")
        st.stop()
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-3-flash-preview')
except Exception as e:
    st.error(f"API Key Error: {e}")

#css
st.markdown("""
<style>
    /* Gradient Background */
    .stApp { background: linear-gradient(135deg, #eef2f3 0%, #8e9eab 100%); }
    
    /* Text Visibility */
    h1, h2, h3, p, div, span, label, li { color: #2c3e50 !important; }
    
    /* Chart Metrics */
    div[data-testid="stMetricValue"] { color: #5D3FD3; font-size: 28px; font-weight: bold; }
    
    /* Chat Bubbles */
    div[data-testid="stChatMessage"] {
        border-radius: 15px; padding: 12px; margin-bottom: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

#functions
def text_to_speech(text, lang='en'):
    """Converts AI text to Audio (skips Odia to prevent crash)."""
    try:
        if lang == "Odia": return None
        lang_code = 'hi' if lang == "Hindi" else 'en'
        tts = gTTS(text=text, lang=lang_code, slow=False)
        filename = "response.mp3"
        tts.save(filename)
        return filename
    except: return None

def analyze_mood_with_score(text):
    """Gets Mood (Word) and Score (1-10) safely."""
    try:
        response = model.generate_content(
            f"Analyze this text: '{text}'. Return a comma-separated string: "
            f"1. The exact emotion (one word). "
            f"2. A positivity score from 1 (Worst) to 10 (Best). "
            f"Example format: 'Frustrated, 3'"
        )
        if response:
            parts = response.text.split(',')
            label = parts[0].strip()
            score = int(parts[1].strip())
            return label, score
        return "Neutral", 5
    except:
        return "Neutral", 5

#sidebar
with st.sidebar:
    st.title("🧠 MindMate Ultimate")
    col1, col2 = st.columns(2)
    with col1:
        language = st.radio("Lang:", ["English", "Hindi", "Odia"])
    with col2:
        st.write("🎙️ **Speak:**")
        audio_bytes = mic_recorder(start_prompt="🔴 Rec", stop_prompt="⏹️ Stop", key='recorder')

    st.markdown("---")
    
    persona = st.selectbox("Mode:", ["Zen Friend (Calm)", "Life Coach (Direct)", "Rational Guide (Logic)"])
    enable_audio = st.checkbox("Enable Audio Reply 🗣️")
    
    st.markdown("---")
    st.subheader("📈 Emotional Trends")
    chart_placeholder = st.empty()

def update_chart():
    """Refreshes the sidebar graph instantly with high-quality settings."""
    if len(st.session_state.mood_log) > 0:
        df = pd.DataFrame(st.session_state.mood_log)
        
        with chart_placeholder.container():
            latest_mood = df.iloc[-1]['Label']
            st.metric("Current Vibe", latest_mood)
            st.vega_lite_chart(df, {
                'mark': {'type': 'line', 'point': True, 'interpolate': 'monotone'}, 
                'encoding': {
                    'x': {'field': 'Time', 'type': 'ordinal', 'axis': {'labels': False}}, 
                    'y': {'field': 'Score', 'type': 'quantitative', 'scale': {'domain': [0, 10]}, 'title': 'Positivity'},
                    'color': {'value': '#764ba2'},
                    'tooltip': [{'field': 'Time'}, {'field': 'Label'}, {'field': 'Score'}]
                }
            }, use_container_width=True)
update_chart()

#audio input
voice_text = ""
if audio_bytes:
    r = sr.Recognizer()
    try:
        with open("temp_audio.wav", "wb") as f:
            f.write(audio_bytes['bytes'])
        with sr.AudioFile("temp_audio.wav") as source:
            r.adjust_for_ambient_noise(source)
            audio_data = r.record(source)
            
            lang_code = "en-US"
            if language == "Hindi": lang_code = "hi-IN"
            if language == "Odia": lang_code = "or-IN"
            voice_text = r.recognize_google(audio_data, language=lang_code)
            st.toast(f"Heard: {voice_text}", icon="👂")
            
    except sr.UnknownValueError:
        st.warning("Could not understand audio. Please speak clearly.")
    except sr.RequestError as e:
        st.error(f"Could not request results from Google Speech Recognition service; {e}")
    except Exception as e:
        st.error(f"Microphone Error: {e}")

####main
st.title(f"MindMate ({language})")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

final_input = voice_text if voice_text else st.chat_input("Type here...")

if final_input:
    st.session_state.messages.append({"role": "user", "content": final_input})
    with st.chat_message("user"):
        st.markdown(final_input)
    mood_label, mood_score = analyze_mood_with_score(final_input)
    st.session_state.mood_log.append({
        "Time": datetime.now().strftime("%H:%M:%S"),
        "Label": mood_label,
        "Score": mood_score
    })
    update_chart() 

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            chat = model.start_chat(history=[])
            
            lang_instr = "Reply in Odia." if language == "Odia" else ("Reply in Hindi." if language == "Hindi" else "Reply in English.")
            final_prompt = f"(System: {persona} mode. {lang_instr} User feels {mood_label}. Keep it short.) User: {final_input}"

            try:
                response = chat.send_message(final_prompt, stream=True)
            except:
                time.sleep(2) 
                response = chat.send_message(final_prompt, stream=True)

            for chunk in response:
                if chunk.text:
                    full_response += chunk.text
                    message_placeholder.markdown(full_response + "▌")
            
            message_placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
            if enable_audio and language != "Odia":
                audio_file = text_to_speech(full_response, language)
                if audio_file:
                    st.audio(audio_file, format="audio/mp3", autoplay=True)
                
        except Exception as e:
            message_placeholder.error(f"Error: {e}")