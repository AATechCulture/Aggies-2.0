import os
import openai
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from datetime import datetime, timedelta
import re
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle
import base64

# Initialize the Flask app
app = Flask(__name__)
app.secret_key = os.urandom(24)  # Securely generate a random session secret key

# Dummy user credentials
USER_CREDENTIALS = {
    "aggie": "1891"
}

# OpenAI API initialization
def init_openai():
    openai.api_key = "sk-your-openai-key-here"  # Replace with your actual OpenAI API key

# Events data (you can replace or modify this with actual data)
events = [
    ('General meeting', datetime(2024, 11, 16, 14, 30)),
    ('Job interview', datetime(2024, 11, 17, 10, 0)),
    ('Conference call', datetime(2024, 11, 18, 16, 0)),
    ('Team lunch', datetime(2024, 11, 19, 12, 0)),
]

# Gmail API: Setup service
def get_gmail_service():
    """Sets up Gmail API authentication and returns the service."""
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    creds = None

    # Load credentials from token.pickle
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # Authenticate if no valid credentials are found
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        # Save credentials for future use
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return build('gmail', 'v1', credentials=creds)

# Gmail API: Fetch recent emails
def read_emails(max_results=10):
    """Fetches recent emails from Gmail and returns their details."""
    try:
        service = get_gmail_service()
        results = service.users().messages().list(userId='me', maxResults=max_results).execute()
        messages = results.get('messages', [])
        emails = []

        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            headers = msg['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')

            # Decode the email body
            body = ''
            if 'parts' in msg['payload']:
                for part in msg['payload']['parts']:
                    if part['mimeType'] == 'text/plain':
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                        break
            elif 'data' in msg['payload']['body']:
                body = base64.urlsafe_b64decode(msg['payload']['body']['data']).decode('utf-8')

            emails.append({'subject': subject, 'from': sender, 'date': date, 'body': body})

        return emails
    except Exception as e:
        print(f"Error in read_emails: {e}")
        return []

# Check if a new event conflicts with existing ones
def check_event_conflict(new_event_time: datetime) -> bool:
    for _, existing_time in events:
        if existing_time.date() == new_event_time.date() and existing_time.hour == new_event_time.hour:
            return True
    return False

# Get time suggestions from OpenAI
def get_openai_suggestion(event_type: str, duration: int) -> str:
    prompt = f"Can you suggest an available time slot for a {event_type} lasting {duration} hours, avoiding the following times: {', '.join([str(event[1]) for event in events])}."

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.5,
        )

        suggestion = response['choices'][0]['message']['content'].strip()
        return suggestion
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return "Sorry, I couldn't generate a time slot."

# Extract datetime from OpenAI response
def extract_datetime_from_response(response: str) -> datetime:
    date_time_match = re.search(r'(\d{4}-\d{2}-\d{2}) at (\d{2}:\d{2}:\d{2})', response)

    if date_time_match:
        date_str = date_time_match.group(1)
        time_str = date_time_match.group(2)

        datetime_str = f"{date_str} {time_str}"

        try:
            return datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None
    return None

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Validate credentials
        if username in USER_CREDENTIALS and USER_CREDENTIALS[username] == password:
            session['logged_in'] = True
            return redirect(url_for('home'))
        else:
            error = "Invalid username or password. Please try again."
            return render_template('login.html', error=error)

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()  # Clear session on logout
    return redirect(url_for('login'))

@app.route('/')
def home():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    now = datetime.now()
    current_date = now if now.month == 11 and now.year == 2024 else datetime(2024, 11, 1)

    # Get the first event in the list for the current day tasks
    first_event = events[0][0] if events else "No events available"

    # Filter upcoming events
    upcoming_events = [event[0] for event in events if event[1] > now]

    return render_template('index.html', current_date=current_date.strftime("%B %d, %Y"), first_event=first_event, upcoming_events=upcoming_events)

@app.route('/ask', methods=['POST'])
def ask():
    user_input = request.form['user_input']
    preferred_time = "1 PM"
    duration = 1

    event_type = get_openai_suggestion(user_input, duration)
    suggested_time_str = get_openai_suggestion(event_type, duration)

    if "sorry" in suggested_time_str.lower():
        response = "Could not suggest a time."
    else:
        suggested_time = extract_datetime_from_response(suggested_time_str)

        if suggested_time:
            if check_event_conflict(suggested_time):
                response = f"Suggested time {suggested_time} conflicts with an existing event. Please choose another time."
            else:
                events.append((event_type, suggested_time))
                response = f"Event '{event_type}' scheduled for {suggested_time}"
        else:
            response = "Could not extract a valid time."

    return jsonify({'response': response})

@app.route('/get-tasks', methods=['GET'])
def get_tasks():
    """API endpoint to fetch tasks from Gmail."""
    try:
        emails = read_emails(max_results=10)
        tasks = []

        for email in emails:
            # Extract tasks from email body
            if 'on' in email['body']:
                try:
                    body_lines = email['body'].splitlines()
                    for line in body_lines:
                        if 'on' in line and 'at' in line:
                            task_details = line.split('on')
                            task_name = task_details[0].strip()
                            date_time = task_details[1].strip()
                            tasks.append({'task': task_name, 'date_time': date_time})
                except Exception as e:
                    print(f"Error parsing task: {e}")

        return jsonify(tasks)
    except Exception as e:
        print(f"Error fetching tasks: {e}")
        return jsonify({'error': 'Failed to fetch tasks'}), 500


if __name__ == '__main__':
    init_openai()
    app.run(debug=True)
