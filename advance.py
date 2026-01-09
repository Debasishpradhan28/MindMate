import streamlit as st
import google.generativeai as genai
import pandas as pd
from datetime import datetime
import time
from gtts import gTTS
import speech_recognition as sr
from streamlit_mic_recorder import mic_recorder
import os

# --- 1. CONFIGURATION ---
st.set_page_config(
    page_title="MindMate Ultimate",
    page_icon="🧠",
    layout="wide"
)

# --- 2. SESSION STATE SETUP ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "I'm here. How are you feeling?"}]
if "mood_log" not in st.session_state:
    # Pre-fill with a starting point so the graph isn't empty
    st.session_state.mood_log = [{"Time": datetime.now().strftime("%H:%M:%S"), "Label": "Neutral", "Score": 5}]

try:
    # Tries to get the key from Streamlit Cloud Secrets
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    # Fallback: Use your local string if running on your laptop
    GOOGLE_API_KEY = "AIzaSyCXgzCqjH3GBJ_PJyYlYgSd-b5fYeQWkYU"

try:
    if "PASTE_YOUR_KEY" in GOOGLE_API_KEY:
        st.error("🚨 STOP: Paste your API Key in line 26!")
        st.stop()
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-3-flash-preview')
except Exception as e:
    st.error(f"API Key Error: {e}")

# --- 3. PROFESSIONAL CSS ---
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

# --- 4. CORE FUNCTIONS ---

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

# --- 5. SIDEBAR (CONTROLS & GRAPH) ---
with st.sidebar:
    st.title("🧠 MindMate Ultimate")
    
    # A. Language & Voice
    col1, col2 = st.columns(2)
    with col1:
        language = st.radio("Lang:", ["English", "Hindi", "Odia"])
    with col2:
        st.write("🎙️ **Speak:**")
        # Mic Recorder
        audio_bytes = mic_recorder(start_prompt="🔴 Rec", stop_prompt="⏹️ Stop", key='recorder')

    st.markdown("---")
    
    # B. Persona
    persona = st.selectbox("Mode:", ["Zen Friend (Calm)", "Life Coach (Direct)", "Rational Guide (Logic)"])
    enable_audio = st.checkbox("Enable Audio Reply 🗣️")
    
    st.markdown("---")
    
    # C. REAL-TIME GRAPH (FIXED)
    st.subheader("📈 Emotional Trends")
    # We create the placeholder HERE, so we can fill it from anywhere
    chart_placeholder = st.empty()

# --- 6. CHART DRAWING LOGIC (RESTORED) ---
def update_chart():
    """Refreshes the sidebar graph instantly with high-quality settings."""
    if len(st.session_state.mood_log) > 0:
        df = pd.DataFrame(st.session_state.mood_log)
        
        with chart_placeholder.container():
            # 1. Metric
            latest_mood = df.iloc[-1]['Label']
            st.metric("Current Vibe", latest_mood)
            
            # 2. The Professional Chart (Vega-Lite)
            st.vega_lite_chart(df, {
                'mark': {'type': 'line', 'point': True, 'interpolate': 'monotone'}, # 'monotone' makes it smooth/curvy
                'encoding': {
                    'x': {'field': 'Time', 'type': 'ordinal', 'axis': {'labels': False}}, # Hide messy timestamps
                    'y': {'field': 'Score', 'type': 'quantitative', 'scale': {'domain': [0, 10]}, 'title': 'Positivity'},
                    'color': {'value': '#764ba2'},
                    'tooltip': [{'field': 'Time'}, {'field': 'Label'}, {'field': 'Score'}]
                }
            }, use_container_width=True)

# Initial Graph Render
update_chart()

# --- 7. INPUT PROCESSING (VOICE -> TEXT) ---
voice_text = ""
if audio_bytes:
    r = sr.Recognizer()
    try:
        with open("temp_audio.wav", "wb") as f: f.write(audio_bytes['bytes'])
        with sr.AudioFile("temp_audio.wav") as source:
            audio_data = r.record(source)
            lang_code = "or-IN" if language == "Odia" else ("hi-IN" if language == "Hindi" else "en-US")
            voice_text = r.recognize_google(audio_data, language=lang_code)
            st.toast(f"Heard: {voice_text}", icon="👂")
    except: st.warning("No audio detected.")

# --- 8. MAIN CHAT LOGIC ---
st.title(f"MindMate ({language})")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- 9. HANDLE INPUT (TEXT OR VOICE) ---
final_input = voice_text if voice_text else st.chat_input("Type here...")

if final_input:
    # A. Display User Message
    st.session_state.messages.append({"role": "user", "content": final_input})
    with st.chat_message("user"):
        st.markdown(final_input)

    # B. ⚡ INSTANT GRAPH UPDATE ⚡
    # We analyze mood AND update the graph BEFORE the AI starts thinking.
    # This fixes the "lag" or "degraded" feeling.
    mood_label, mood_score = analyze_mood_with_score(final_input)
    st.session_state.mood_log.append({
        "Time": datetime.now().strftime("%H:%M:%S"),
        "Label": mood_label,
        "Score": mood_score
    })
    update_chart() # <--- Force refresh immediately

    # C. Generate AI Response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            chat = model.start_chat(history=[])
            
            # System Prompt Construction
            lang_instr = "Reply in Odia." if language == "Odia" else ("Reply in Hindi." if language == "Hindi" else "Reply in English.")
            final_prompt = f"(System: {persona} mode. {lang_instr} User feels {mood_label}. Keep it short.) User: {final_input}"
            
            # Streaming Response
            try:
                response = chat.send_message(final_prompt, stream=True)
            except:
                time.sleep(2) # Anti-Crash Wait
                response = chat.send_message(final_prompt, stream=True)

            for chunk in response:
                if chunk.text:
                    full_response += chunk.text
                    message_placeholder.markdown(full_response + "▌")
            
            message_placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
            # D. Audio Output (If Enabled)
            if enable_audio and language != "Odia":
                audio_file = text_to_speech(full_response, language)
                if audio_file:
                    st.audio(audio_file, format="audio/mp3", autoplay=True)
                
        except Exception as e:
            message_placeholder.error(f"Error: {e}")