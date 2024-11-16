import os
import openai
from flask import Flask, request, jsonify, render_template, redirect, url_for
from datetime import datetime, timedelta
import re

app = Flask(__name__)

# Initialize OpenAI API key (ensure to use environment variables or another secure method in production)
def init_openai():
    openai.api_key = "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" # Replace with your actual OpenAI API key

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

# Function to extract datetime from OpenAI response
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

# Function to extract event type from OpenAI response
def get_event_type_from_openai(text: str) -> str:
    prompt = f"Please extract the event type from the following text: '{text}'"

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50,
            temperature=0.5,
        )

        event_type = response['choices'][0]['message']['content'].strip()
        return event_type
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return "Unrecognized Event"

# Function to handle date navigation (forward/backward)
def update_date(current_date, direction):
    # Define the first and last date of November 2024
    first_november = datetime(2024, 11, 1)
    last_november = datetime(2024, 11, 30)

    if direction == 'forward' and current_date < last_november:
        current_date += timedelta(days=1)
    elif direction == 'backward' and current_date > first_november:
        current_date -= timedelta(days=1)

    return current_date

# Flask route to handle chatbot interaction
@app.route('/')
def home():
    # Get the current date and time
    now = datetime.now()

    # Restrict the date to November 2024
    current_date = now if now.month == 11 and now.year == 2024 else datetime(2024, 11, 1)

    # Get the first event in the list for the current day tasks
    if events:
        first_event = events[0][0]
    else:
        first_event = "No events available"

    # Filter upcoming events (those occurring after the current time)
    upcoming_events = [event[0] for event in events if event[1] > now]

    return render_template('index.html', current_date=current_date.strftime("%B %d, %Y"), first_event=first_event, upcoming_events=upcoming_events)

# Route to navigate between days
@app.route('/navigate/<direction>')
def navigate(direction):
    # Get the current date from the query string (or default to today's date)
    current_date = datetime(2024, 11, 1)  # Starting date for November 2024
    # Update the date based on the direction (forward/backward)
    updated_date = update_date(current_date, direction)

    return redirect(url_for('home', current_date=updated_date.strftime("%Y-%m-%d")))

@app.route('/ask', methods=['POST'])
def ask():
    user_input = request.form['user_input']
    preferred_time = "1 PM"  # Hardcoded for simplicity
    duration = 1  # 1 hour

    event_type = get_event_type_from_openai(user_input)
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

if __name__ == '__main__':
    init_openai()  # Ensure the API key is initialized
    app.run(debug=True)
