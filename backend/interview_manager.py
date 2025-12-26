import os
import tempfile
from dotenv import load_dotenv
from openai import OpenAI
from gtts import gTTS
from faster_whisper import WhisperModel

load_dotenv()

client_llm = OpenAI(
    api_key=os.environ.get("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)

MODEL_SIZE = "base.en" 

print("Loading Whisper Model..")
stt_model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
print("Whisper Model Loaded!")


def text_to_speech(text):
    """Converts AI text to an Audio file using Google TTS (Free)"""
    try:
        tts = gTTS(text=text, lang='en')
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tts.save(temp_file.name)
        return temp_file.name
    except Exception as e:
        print(f"TTS Error: {e}")
        return None


def transcribe_audio(audio_bytes):
    """Converts User Audio to Text using Faster-Whisper (Local)"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            temp_audio.write(audio_bytes)
            temp_audio_path = temp_audio.name

        segments, info = stt_model.transcribe(temp_audio_path, beam_size=5)

        full_text = " ".join([segment.text for segment in segments])
        
        os.remove(temp_audio_path)
        
        return full_text.strip()
    except Exception as e:
        return f"Error transcribing: {str(e)}"


def generate_interview_question(history, resume_text, job_desc):
    """Generates the next question based on conversation history"""
    
    system_prompt = f"""
    You are a professional Interviewer conducting a voice interview.
    
    JOB DESCRIPTION:
    {job_desc}
    
    CANDIDATE RESUME:
    {resume_text}
    
    YOUR GOAL:
    - Ask ONE relevant interview question at a time.
    - Start with a greeting and a question about their background.
    - After background question, ask questions related to the job description.
    - Based on their answers, ask follow-up questions to dig deeper.
    - If they struggle, offer hints or simpler sub-questions.
    - Based on their previous answer, ask a follow-up or move to a technical skill.
    - Keep questions concise (short sentences are better for TTS).
    - Do NOT write long paragraphs. Keep it conversational.
    - Avoid repeating questions already asked.
    - Maintain a friendly and encouraging tone.
    - Ensure questions are relevant to the job description and resume.
    - If you run out of questions, politely end the interview.
    - Always wait for the candidate's answer before asking the next question.
    - If the candidate does not answer or does not know the answer or give wrong answer or goes off-topic, ask another question.
    - At the end of the interview, ask behavioral questions related to teamwork and problem-solving.
    - At the end, ask if they have any questions for you.
    - If candidate have questions related to HR/policy/salary/company, politely inform them that those will be discussed by HR later.
    - At the end of the interview, thank the candidate for their time and tell them you will be in touch soon.
    """

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)

    try:
        response = client_llm.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=messages,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return "Let's move to the next topic. Can you tell me about your strengths?"