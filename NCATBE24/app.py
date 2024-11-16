import os
import openai
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from datetime import datetime, timedelta
import re
from main import add_event_with_reminders, get_event_type_from_openai

import re
from datetime import datetime



# Dummy user credentials
USER_CREDENTIALS = {
    "aggie": "1891"
}

def refine_event_type(event_type: str) -> str:
    """
    Refines the event type based on more specific keywords.
    """
    if "dentist" in event_type.lower():
        return "Dentist appointment"
    elif "pill" in event_type.lower():
        return "Pill appointment"
    elif "doctor" in event_type.lower() or "visit" in event_type.lower():
        return "Doctor's visit"
    elif "coffee" in event_type.lower():
        return "Coffee meeting"
    elif "zoom" in event_type.lower():
        return "Zoom meeting"
    elif "meeting" in event_type.lower():
        return "General meeting"
    elif "interview" in event_type.lower():
        return "Job interview"
    elif "conference" in event_type.lower():
        return "Conference call"
    elif "lunch" in event_type.lower():
        return "Team lunch"
    elif "study" in event_type.lower():
        return "Study session"


    return "Unrecognized Event"


def extract_datetime_from_input(input_string: str) -> datetime:
    """
    Extracts the date and time from the user input string.
    """
    # Match patterns like "3 PM on November 20th"
    match = re.search(r'(\d{1,2})\s*(AM|PM)\s*on\s*(\w+\s\d{1,2}(?:st|nd|rd|th)?)', input_string)
    if match:
        hour = int(match.group(1))
        period = match.group(2)
        date_str = match.group(3)

        # Handle AM/PM formatting
        if period == "PM" and hour != 12:
            hour += 12
        elif period == "AM" and hour == 12:
            hour = 0

        # Parse the date
        try:
            date_obj = datetime.strptime(date_str, "%B %d").replace(year=datetime.now().year)
            return date_obj.replace(hour=hour)
        except ValueError as ve:
            print(f"Error parsing date: {ve}")

    return None


# Initialize Flask app
app = Flask(__name__)

# Initialize OpenAI API key
openai.api_key = "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"

#session['logged_in'] = False
app.secret_key = 'your_secret_key'  # Necessary for session management
# List to store events
events = [
    ('General meeting', datetime(2024, 11, 16, 14, 30)),
    ('Job interview', datetime(2024, 11, 17, 10, 0)),
    ('Conference call', datetime(2024, 11, 18, 16, 0)),
    ('Team lunch', datetime(2024, 11, 19, 12, 0)),
]

# Function to check if the proposed time conflicts with any existing event
def check_event_conflict(new_event_time: datetime) -> bool:
    for _, existing_time in events:
        if existing_time.date() == new_event_time.date() and existing_time.hour == new_event_time.hour:
            return True
    return False


# Function to get suggestions from OpenAI about available time slots
def get_openai_suggestion(event_type: str, duration: int) -> str:
    # Prompt the user to suggest a time, but leave it open to OpenAI to propose an available time.
    prompt = f"Can you suggest an available time slot for a {event_type} lasting {duration} hours, avoiding the following times: {', '.join([str(event[1]) for event in events])}. The user suggested a time of today for the event."

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


# Function to extract datetime from OpenAI response
def extract_datetime_from_response(response: str) -> datetime:
    date_time_match = re.search(r'(\w+ \d{1,2}) at (\d{1,2}:\d{2} (AM|PM))', response)
    if date_time_match:
        date_str = date_time_match.group(1)
        time_str = date_time_match.group(2)
        month_map = {
            "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
            "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12
        }
        try:
            month, day = date_str.split()
            month = month_map[month]
            day = int(day)
            current_year = datetime.now().year
            parsed_time = datetime.strptime(time_str, "%I:%M %p").time()
            return datetime(current_year, month, day, parsed_time.hour, parsed_time.minute)
        except ValueError as ve:
            print(f"Error parsing date and time: {ve}")
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
@app.route('/index')
def logout():
    session.clear()  # Clear the session
    session['logged_in'] = False
    return redirect(url_for('login'))

@app.route('/')
def home():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    current_date = datetime.now().strftime('%A, %B %d, %Y')
    first_event = events[0][0] if events else "No events scheduled."
    upcoming_events = [event[0] for event in events[1:]]
    today_tasks = [event for event in events if event[1].date() == datetime.today().date()]
    return render_template('index.html', current_date=current_date, first_event=first_event,
                           upcoming_events=upcoming_events, today_tasks=today_tasks)

@app.route('/calendar')
def calendar():
    return render_template('calendar.html')

@app.route('/ask', methods=['POST'])
def ask():
    user_input = request.form.get('user_input')
    if not user_input:
        return jsonify({"response": "Please provide input."})

    # Regular response from OpenAI (for Chatbot)
    response = get_openai_suggestion(user_input, 1)  # Example duration of 1 hour
    response_arr = response.split()

    # Refine the event type (for Today's Tasks)
    res = ""
    for string in response_arr:
        res = refine_event_type(string)
        if res != "Unrecognized Event":
            break

    time_of_task = ""
    for string in response_arr:
        if ("PM" or "AM") in string.upper():
             time_of_task += string

    # Extract the event date using the input (not relying on the OpenAI response here)
    event_date = extract_datetime_from_input(user_input)  # Extract the event's date and time from user input

    reminder_message = ""
    if res != "Unrecognized Event" and event_date:
        # Add the event with reminders
        add_event_with_reminders(res, event_date)
        reminder_message = f"Reminder: {res} at {event_date.strftime('%I:%M %p')}"

    # Return both the response for Chatbot and the task event for Today's Tasks
    return jsonify({
        "chatbot_response": response,  # Raw response from OpenAI (for Chatbot)
        "reminder_message": reminder_message,
        "task_event": f"{res} - {time_of_task}",  # Refined task (for Today's Tasks)
    })


if __name__ == '__main__':
    app.run(debug=True)
