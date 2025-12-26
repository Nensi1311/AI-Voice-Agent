import os
import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

# Config
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Send Email Logic
def send_confirmation_email(candidate_name, candidate_email, start_time):
    subject = f"Interview Invitation: {candidate_name}"
    formatted_time = start_time.strftime("%A, %B %d at %H:%M")
    
    body = f"""
    Hi {candidate_name},

    We have reviewed your profile and would like to invite you for an interview!

    📅 Scheduled Time: {formatted_time}

    Please reply to this email to confirm your availability. If you are unable to attend at this time, let us know on which date and time you would be available.

    Best regards,
    Hiring Team
    """

    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = candidate_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Mail Error: {e}")
        return False

# Main Batch Function 
def batch_schedule_interviews(selected_candidates, start_datetime_obj):
    logs = []
    current_time = start_datetime_obj
    GAP_MINUTES = 10
    DURATION_MINUTES = 30

    for cand in selected_candidates:
        name = cand['name']
        email = cand['email']

        if "No Email" in email or email == "None":
            logs.append(f"⚠️ Skipped {name} (No Email)")
            continue

        # Send Email
        success = send_confirmation_email(name, email, current_time)
        
        if success:
            logs.append(f"Email Sent: **{name}** for {current_time.strftime('%H:%M')}")
            # Increment Time (30 min interview + 10 min gap)
            current_time += datetime.timedelta(minutes=DURATION_MINUTES + GAP_MINUTES)
        else:
            logs.append(f"Email Failed: {name} (Check Password/Internet)")

    return logs