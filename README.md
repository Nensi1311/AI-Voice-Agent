# SmartHire Assistant

An AI-powered hiring assistant that streamlines the recruitment process by analyzing resumes, scheduling interviews, and conducting live voice interviews with candidates.

## Features

### Resume Analysis
- Upload multiple PDF resumes
- AI-powered matching against job requirements
- Automatic candidate scoring (0-100)
- Extracts candidate name, email and generates summaries
- Interactive table view with candidate selection

### Interview Scheduler
- Batch schedule multiple interviews
- Automatic email invitations to candidates
- Configurable interview time slots (30-minute interviews with 10-minute gaps)

### AI Voice Interview
- Real-time voice-to-text transcription using Faster-Whisper
- AI-generated interview questions based on resume and job description
- Text-to-speech responses using Google TTS
- Context-aware follow-up questions
- Conversation history management

### Chat Interface
- Persistent chat sessions
- Session management (create, rename, delete)
- Chat history with resume analysis results
- Modern, responsive UI

## Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - Database ORM
- **PostgreSQL** (with SQLite fallback) - Database
- **OpenAI GPT-4o-mini** (via OpenRouter) - AI model for resume analysis and interview questions
- **Faster-Whisper** - Speech-to-text transcription
- **gTTS** - Text-to-speech conversion
- **PyPDF** - PDF text extraction
- **SMTP** - Email sending

### Frontend
- **Vanilla JavaScript** - Client-side logic
- **Tailwind CSS** - Styling
- **Font Awesome** - Icons

### Alternative UI
- **Streamlit** - Python-based web interface

## Prerequisites

- Python 3.8+
- PostgreSQL (optional, SQLite fallback available)

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd AI-Voice-Agent
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   
   Create a `.env` file in the root directory:
   ```env
   # AI API Configuration
   OPENROUTER_API_KEY=your_openrouter_api_key_here
   
   # Database Configuration (optional)
   POSTGRES_DB_URL=postgresql://user:password@localhost:5432/smarthire
   
   # Email Configuration (for scheduler)
   SENDER_EMAIL=your_email@gmail.com
   SENDER_PASSWORD=your_app_password_here
   ```

   **Note:** For Gmail, you'll need to generate an [App Password](https://support.google.com/accounts/answer/185833) instead of your regular password.

4. **Initialize the database**
   
   The database tables will be created automatically on first run. If using PostgreSQL, make sure the database exists:
   ```sql
   CREATE DATABASE smarthire;
   ```

## Running the Application

### Option 1: FastAPI Backend with Web Frontend

1. **Start the FastAPI server**
   ```bash
   cd backend
   python main.py
   ```
   
   Or using uvicorn directly:
   ```bash
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Access the application**
   
   Open your browser and navigate to:
   ```
   http://localhost:8000
   ```

   The FastAPI server serves both the API endpoints and the static frontend files.

### Option 2: Streamlit Interface

1. **Run Streamlit app**
   ```bash
   streamlit run streamlit/app.py
   ```

2. **Access the application**
   
   The Streamlit interface will open automatically in your browser, typically at:
   ```
   http://localhost:8501
   ```

## Usage Guide

### Resume Analysis

1. **Upload Resumes**
   - Click the "+" button in the chat input area
   - Select one or more PDF resume files
   - Files will appear as chips above the input field

2. **Enter Job Requirements**
   - Type your job requirements in the chat input
   - Example: "Need a Senior Python Developer with AWS experience"
   - Press Enter or click the send button

3. **Review Results**
   - The AI will analyze all resumes and display results in a table
   - Each candidate shows: Name, Email, Match Score, and Summary
   - Select candidates you want to interview using checkboxes
   - Click "Proceed to Scheduler" to move selected candidates

### Interview Scheduling

1. **Select Candidates**
   - Go to the Scheduler tab
   - Review the selected candidates from the Analysis tab
   - Or manually select candidates from the analysis results

2. **Set Interview Details**
   - Choose start date and time
   - Enter meeting link (Zoom/Teams/Google Meet)
   - Click "Send Invites"

3. **Email Confirmation**
   - The system will send email invitations to all selected candidates
   - Interviews are scheduled with 10-minute gaps between candidates
   - Check the logs for email delivery status

### AI Voice Interview

1. **Start Interview Session**
   - Navigate to the Interview tab
   - Select a candidate from the dropdown
   - Click "Start Interview Session"

2. **Conduct Interview**
   - Click and hold the microphone button to speak
   - Release to stop recording
   - The AI will transcribe your answer and ask follow-up questions
   - Listen to AI responses via text-to-speech

3. **Interview Flow**
   - Questions are generated based on the candidate's resume
   - The AI adapts questions based on previous answers
   - Interview ends when appropriate questions are exhausted

## API Endpoints

### Resume Analysis
- `POST /api/analyze` - Analyze resumes against job requirements
  - Form data: `job_description`, `session_id` (optional), `resumes` (files)

### Interview Management
- `POST /api/interview/transcribe` - Transcribe audio to text
  - Form data: `audio` (file)
- `POST /api/interview/chat` - Generate interview question
  - JSON: `user_text`, `session_id`, `job_desc`, `resume_text`

### Scheduling
- `POST /api/schedule` - Schedule interviews and send emails
  - JSON: `candidates` (array), `start_time`

### Session Management
- `GET /api/sessions` - Get all chat sessions
- `GET /api/history/{session_id}` - Get chat history for a session
- `PUT /api/sessions/{session_id}` - Rename a session
- `DELETE /api/sessions/{session_id}` - Delete a session
- `POST /api/reset` - Delete all sessions

## Project Structure

```
AI-Voice-Agent/
├── backend/
│   ├── main.py                 # FastAPI application and API endpoints
│   ├── analyze_and_summary.py  # Resume analysis logic
│   ├── interview_manager.py    # Voice interview and TTS/STT
│   └── scheduler.py            # Email scheduling functionality
├── frontend/
│   ├── index.html              # Main HTML file
│   └── app.js                  # Frontend JavaScript logic
├── streamlit/
│   └── app.py                  # Streamlit alternative UI
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## Troubleshooting

### Whisper Model Loading
- First run will download the Faster-Whisper model (~150MB)
- Ensure you have sufficient disk space
- Model loads on CPU by default (can be slow on first transcription)

### Email Not Sending
- Verify `SENDER_EMAIL` and `SENDER_PASSWORD` in `.env`
- For Gmail, ensure you're using an App Password, not your regular password
- Check firewall settings for SMTP port 587

### Database Connection Issues
- If PostgreSQL connection fails, the app will fall back to SQLite
- SQLite database file (`app.db`) will be created in the backend directory
- For production, use PostgreSQL for better performance