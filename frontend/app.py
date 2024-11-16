import os
import pickle
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, jsonify, request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# Initialize Flask app
app = Flask(__name__)

CLIENT_SECRET_FILE = 'credentials2.json'
SCOPES = ['https://www.googleapis.com/auth/calendar']

# Authentication to Google Calendar API
def authenticate_google_calendar():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=5001)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    service = build('calendar', 'v3', credentials=creds)
    return service

# Function to fetch events from Google Calendar
def get_google_calendar_events(service, start_date, end_date):
    events_result = service.events().list(
        calendarId='primary',
        timeMin=start_date.isoformat(),
        timeMax=end_date.isoformat(),
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    events = []
    for event in events_result.get('items', []):
        event_start = event['start'].get('dateTime', event['start'].get('date'))
        event_type = event.get('summary', 'No title')
        events.append({
            'title': event_type,
            'start': event_start,
            'end': event['end'].get('dateTime', event['end'].get('date')),
        })
    return events

@app.route('/')
def index():
    # Get current time in EST
    current_time_est = datetime.now(timezone(timedelta(hours=-5), 'EST')).strftime("%H:%M:%S")

    # Authenticate with Google Calendar
    service = authenticate_google_calendar()

    # Get today's date and the next 30 days
    today = datetime.today()
    end_date = today + timedelta(days=30)

    # Fetch events from Google Calendar
    events = get_google_calendar_events(service, today, end_date)

    # Pass the current time and events to the template
    return render_template('index.html', current_date=current_time_est, events=events)

@app.route('/api/events', methods=['GET'])
def events():
    service = authenticate_google_calendar()

    # Get today's date and the next 30 days
    today = datetime.today()
    end_date = today + timedelta(days=30)

    # Fetch events from Google Calendar
    events = get_google_calendar_events(service, today, end_date)

    return jsonify(events)

@app.route('/api/events/<date>', methods=['GET'])
def get_events_for_day(date):
    service = authenticate_google_calendar()

    # Parse the requested date
    selected_date = datetime.strptime(date, '%Y-%m-%d')
    end_date = selected_date + timedelta(days=1)

    # Fetch events for the selected day
    events = get_google_calendar_events(service, selected_date, end_date)

    return jsonify(events)

if __name__ == '__main__':
    app.run(debug=True)
