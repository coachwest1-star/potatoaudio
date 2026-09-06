from datetime import datetime, timezone
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

creds = Credentials.from_authorized_user_file(
    '/var/lib/potato-audio/google-token.json',
    SCOPES
)

service = build('calendar', 'v3', credentials=creds)

now = datetime.now(timezone.utc).isoformat()

events = service.events().list(
    calendarId='primary',
    timeMin=now,
    maxResults=10,
    singleEvents=True,
    orderBy='startTime'
).execute().get('items', [])

if not events:
    print("No upcoming events found.")
else:
    for e in events:
        start = e['start'].get('dateTime', e['start'].get('date'))
        print(start, '-', e.get('summary', '(No title)'))
