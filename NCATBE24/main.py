import os
import openai
from datetime import datetime
import re


def init_openai() -> None:
    """
    Initialize OpenAI API key from environment variables.
    """
    openai.api_key = "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"


# Function to get event type using OpenAI's chat model (GPT-3 or GPT-4)
def get_event_type_from_openai(text: str) -> str:
    """
    Query the OpenAI API to extract event types from the provided text.
    """
    prompt = f"Please extract the event type (e.g., 'dentist appointment', 'pill appointment', 'doctor's visit', 'Zoom meeting', etc.) from the following text: '{text}'."

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Using the gpt-3.5-turbo model
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50,
            temperature=0.5,
        )

        event_type = response['choices'][0]['message']['content'].strip()

        # Refine event type to be more specific based on keywords
        event_type = refine_event_type(event_type)

        return event_type
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return "Unrecognized Event"


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

    return "Unrecognized Event"


def parse_email_content(email_text: str) -> list[tuple[str, datetime]]:
    """
    Parse email content to extract event types and their corresponding dates and times.
    """
    events = []

    # Regex pattern to capture events with dates and times (e.g., "meeting on November 10, 2024 at 2:30 PM")
    event_pattern = r'([A-Za-z\s]+?)\s+on\s+([A-Za-z]+)\s(\d{1,2}),\s(\d{4})\s+at\s+(\d{1,2}:\d{2}\s?[APMapm]{2})'
    matches = re.findall(event_pattern, email_text)

    print("Matches Found:", matches)  # Debugging line

    for match in matches:
        raw_event_text = match[0].strip()
        event_type = get_event_type_from_openai(raw_event_text)

        # Construct the full date string from the matched groups
        date_string = f"{match[1]} {match[2]}, {match[3]} {match[4]}"

        try:
            # Parse the matched date and time into a datetime object
            event_date = datetime.strptime(date_string, '%B %d, %Y %I:%M %p')
            events.append((event_type, event_date))
        except ValueError as e:
            print(f"Error parsing date and time: {date_string} - {e}")


    return events



if __name__ == "__main__":
    init_openai()

    # Test input (example email content with time included)
    user_input = "Hey Shon, you have a study meeting on November 10, 2024 at 2:30 PM, a job interview on November 17, 2024 at 10:00 AM, a conference call on November 18, 2024 at 4:00 PM, and a team lunch on November 19, 2024 at 12:00 PM."

    # Parse the user input for event dates along with event type and time
    event_dates = parse_email_content(user_input)
    print("Extracted Event Dates:", event_dates)

    # with open("templates/index.html", "r") as keepUpHTML: