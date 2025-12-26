import os
from pypdf import PdfReader
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

openrouter_api_key = os.environ.get("OPENROUTER_API_KEY")

client = OpenAI(
    api_key=openrouter_api_key,
    base_url="https://openrouter.ai/api/v1",
)

def extract_text_from_pdf(uploaded_file):
    try:
        pdf_reader = PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        return str(e)

def analyze_resumes(job_requirements, uploaded_resumes):
    """
    Returns: [{"name": str, "email": str, "score": str, "summary": str}, ...]
    """
    results = []

    # If no resumes are uploaded but text is provided, handle gracefully or return empty
    if not uploaded_resumes:
        return []

    for resume_file in uploaded_resumes:
        resume_text = extract_text_from_pdf(resume_file)
        
        # Updated Prompt: Explicitly instruct AI to look for email in job_requirements (user input) too
        prompt = f"""
        You are an expert HR AI Agent. 
        
        USER INPUT / JOB REQUIREMENTS:
        "{job_requirements}"
        
        CANDIDATE RESUME TEXT:
        "{resume_text}"
        
        Task:
        1. Extract the candidate's full name from the Resume.
        2. Extract the candidate's email. 
           - First, look for the email in the CANDIDATE RESUME.
           - If NOT found in the resume, check the 'USER INPUT' above to see if the user provided an email address there.
           - If found in neither, write "No Email".
        3. Give a match score (0-100) based on how well the resume matches the requirements in USER INPUT.
        4. Write a concise summary (3-4 lines) justifying the score.
        5. Return ONLY this format (use '||' as separator): Name || Email || Score || Summary
        
        Example: "John Doe || john@example.com || 85 || John has strong Python skills..."
        """

        try:
            response = client.chat.completions.create(
                model="openai/gpt-4o-mini", 
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                extra_headers={
                    "HTTP-Referer": "https://localhost:8501", 
                    "X-Title": "Resume Matcher Agent",
                }
            )
            
            content = response.choices[0].message.content.strip()
            
            # Default structure
            candidate_data = {
                "name": "Unknown", 
                "email": "No Email", 
                "score": "0", 
                "summary": "Could not generate summary."
            }

            # Use double pipe || to avoid conflict with text in summary
            if "||" in content:
                parts = content.split("||")
                if len(parts) >= 4:
                    candidate_data = {
                        "name": parts[0].strip(),
                        "email": parts[1].strip(),
                        "score": parts[2].strip(),
                        "summary": parts[3].strip()
                    }
                else:
                    candidate_data["name"] = parts[0].strip()
            
            results.append(candidate_data)
                
        except Exception as e:
            results.append({"name": f"Error {resume_file.name}", "email": "-", "score": "0", "summary": str(e)})

    # Sort results by score
    results.sort(key=lambda x: int(x['score']) if x['score'].isdigit() else 0, reverse=True)
    
    return results