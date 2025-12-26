import streamlit as st
import datetime

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.analyze_and_summary import analyze_resumes
from backend.scheduler import batch_schedule_interviews
from backend.interview_manager import text_to_speech, transcribe_audio, generate_interview_question
from streamlit_mic_recorder import mic_recorder

# 1. Page Configuration
st.set_page_config(page_title="SmartHire Assistant", page_icon="🤖", layout="centered")

# 2. CUSTOM CSS
st.markdown("""
    <style>
        .fixed-header {
            position: fixed;
            top: 0; left: 0; width: 100%;
            background-color: #ffffff;
            z-index: 9999; text-align: center;
            padding: 35px 0;
            box-shadow: 0px 2px 5px rgba(0,0,0,0.1);
            border-bottom: 1px solid #e0e0e0;
        }
        @media (prefers-color-scheme: dark) {
            .fixed-header { background-color: #0E1117; border-bottom: 1px solid #262730; }
        }
        .block-container { padding-top: 130px !important; padding-bottom: 70px; }
    </style>
    <div class="fixed-header"><h1 style="margin: 0; font-size: 2.2rem;">🤖 SmartHire Assistant</h1></div>
""", unsafe_allow_html=True)


# 3. Initialize Session State 
if "messages" not in st.session_state: st.session_state.messages = [{"role": "assistant", "content": "👋 Hello! Upload resumes in the sidebar to start."}]
if "resumes" not in st.session_state: st.session_state.resumes = []
if "candidates" not in st.session_state: st.session_state.candidates = []

# Interview Session State
if "interview_history" not in st.session_state: st.session_state.interview_history = []
if "interview_active" not in st.session_state: st.session_state.interview_active = False
if "current_candidate_resume" not in st.session_state: st.session_state.current_candidate_resume = ""
if "job_context" not in st.session_state: st.session_state.job_context = ""


# 4. Sidebar Logic
with st.sidebar:
    st.header("📂 Upload Resume(s)")
    uploaded_files = st.file_uploader("Upload PDF Resumes", type=["pdf"], accept_multiple_files=True)
    if uploaded_files: st.session_state.resumes = uploaded_files
    st.divider()
    if st.button("🗑️ Reset System"):
        st.session_state.messages = []
        st.session_state.candidates = []
        st.session_state.interview_history = []
        st.session_state.interview_active = False
        st.rerun()


# 5. TABS LOGIC
tab1, tab2, tab3 = st.tabs(["💬 Analysis", "📅 Scheduler", "🎤 AI Interview"])


# TAB 1: Chat Interface
with tab1:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"], unsafe_allow_html=True)

    if prompt := st.chat_input("Ex: 'Need a Senior Python Dev with AWS experience'"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)

        if not st.session_state.resumes:
            st.error("⚠️ Please upload resumes first!")
        else:
            with st.chat_message("assistant"):
                with st.spinner("🧠 Analyzing candidates..."):
                    results = analyze_resumes(prompt, st.session_state.resumes)
                    st.session_state.candidates = results
                    
                    header = f"**Found {len(results)} matches.** \n\nGo to **Scheduler Dashboard** to email them."
                    st.markdown(header)
                    history_text = header + "\n\n"
                    for r in results:
                        with st.expander(f"🏆 Score: {r['score']} - {r['name']}"):
                            st.markdown(f"📧 **Email:** `{r['email']}`")
                            st.info(f"**Summary:**\n{r['summary']}")
                        history_text += f"- **{r['name']}** ({r['score']}): {r['summary'][:100]}...\n"
                    st.success("✅ Candidates sent to Scheduler Dashboard (Tab 2)")
            st.session_state.messages.append({"role": "assistant", "content": history_text})

# TAB 2: Scheduler Interface
with tab2:
    st.header("📅 Schedule Interviews")
    
    if not st.session_state.candidates:
        st.info("👈 Please go to the **Chat Tab** and analyze some resumes first.")
    else:
        st.write("Select the candidates you want to interview below:")
        
        with st.form("schedule_form"):
            selected_indices = []
            for idx, cand in enumerate(st.session_state.candidates):
                is_checked = int(cand['score']) >= 70
                if st.checkbox(f"{cand['name']} (Score: {cand['score']})", value=is_checked, key=f"c_{idx}"):
                    selected_indices.append(idx)
            
            st.divider()
            
            c1, c2 = st.columns(2)
            with c1:
                start_date = st.date_input("Interview Date", datetime.date.today() + datetime.timedelta(days=1))
            with c2:
                start_time = st.time_input("Start Time (First Interview)", datetime.time(10, 0))
            
            # Input for Meeting Link
            meeting_link = st.text_input("Meeting Link (Zoom/Teams/Meet)", "https://meet.google.com/abc-xyz")
            
            st.caption("ℹ️ Emails will be sent with 10-minute gaps between candidates.")
            
            if st.form_submit_button("🚀 Confirm & Send Invites"):
                if not selected_indices:
                    st.warning("Please select at least one candidate.")
                else:
                    final_candidates = [st.session_state.candidates[i] for i in selected_indices]
                    start_dt = datetime.datetime.combine(start_date, start_time)
                    
                    with st.spinner("Sending Emails..."):
                        # Passing 3 arguments now
                        logs = batch_schedule_interviews(final_candidates, start_dt, meeting_link)
                    
                    for log in logs:
                        if "✅" in log: st.success(log)
                        else: st.error(log)

with tab3:
    st.header("🎤 Live Voice Interview")

    if not st.session_state.candidates:
        st.warning("Please analyze resumes in Tab 1 first to identify candidates.")
    else:
        # 1. Select Candidate to Interview
        candidate_names = [c["name"] for c in st.session_state.candidates]
        selected_name = st.selectbox("Select Candidate to Interview:", candidate_names)
        
        # Start Button
        if st.button("▶️ Start Interview Session"):
            st.session_state.interview_active = True
            st.session_state.interview_history = []
            
            cand_data = next(c for c in st.session_state.candidates if c["name"] == selected_name)
            st.session_state.current_candidate_resume = cand_data['summary'] 
            
            # Generate First Question
            first_q = generate_interview_question([], st.session_state.current_candidate_resume, st.session_state.job_context)
            st.session_state.interview_history.append({"role": "assistant", "content": first_q})
            st.rerun()

        st.divider()

        # 2. Interview Loop Display
        if st.session_state.interview_active:
            
            # Display History (Script)
            for msg in st.session_state.interview_history:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])
                    if msg["role"] == "assistant":
                        audio_path = text_to_speech(msg["content"])
                        if audio_path:
                            st.audio(audio_path, format="audio/mp3", start_time=0)

            # 3. User Voice Input
            st.write("🗣️ Your Answer")
            audio_data = mic_recorder(
                start_prompt="🎤 Click to Speak Answer",
                stop_prompt="⏹️ Stop Recording", 
                just_once=False,
                key="recorder"
            )

            if audio_data:
                # Transcribe
                with st.spinner("👂 Listening and transcribing..."):
                    text_answer = transcribe_audio(audio_data['bytes'])
                
                # Append User Answer to History
                st.session_state.interview_history.append({"role": "user", "content": text_answer})
                
                # Generate AI Follow-up
                with st.spinner("🤖 Thinking of next question..."):
                    next_q = generate_interview_question(
                        st.session_state.interview_history, 
                        st.session_state.current_candidate_resume, 
                        st.session_state.job_context
                    )
                    st.session_state.interview_history.append({"role": "assistant", "content": next_q})
                
                st.rerun()