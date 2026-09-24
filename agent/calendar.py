from datetime import datetime, timezone
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


SCOPES = [
    "https://www.googleapis.com/auth/calendar.events"
]

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CREDENTIALS_FILE = os.path.join(
    BASE_DIR,
    "credentials.json"
)

TOKEN_FILE = os.path.join(
    BASE_DIR,
    "token.json"
)

# fax a conexão com a agenda do usuário
def get_calendar_service():
    credentials = None

    if os.path.exists(TOKEN_FILE):
        credentials = Credentials.from_authorized_user_file(
            TOKEN_FILE,
            SCOPES
        )

    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())

    if not credentials or not credentials.valid:

        flow = InstalledAppFlow.from_client_secrets_file(
            CREDENTIALS_FILE,
            SCOPES
        )

        credentials = flow.run_local_server(port=0)

    with open(TOKEN_FILE, "w") as token:
        token.write(credentials.to_json())

    return build(
        "calendar",
        "v3",
        credentials=credentials
    )

# Função para obter eventos do Google Calendar em um intervalo de datas
def get_calendar_events(start_datetime, end_datetime):

    service = get_calendar_service()

    events_result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=start_datetime,
            timeMax=end_datetime,
            singleEvents=True,
            orderBy="startTime",
            maxResults=50
        )
        .execute()
    )

    events = events_result.get("items", [])

    formatted_events = []

    for event in events:

        start = event.get("start", {})
        end = event.get("end", {})

        start_time = start.get(
            "dateTime",
            start.get("date")
        )

        end_time = end.get(
            "dateTime",
            end.get("date")
        )

        formatted_events.append({
            "id": event.get("id"),
            "title": event.get(
                "summary",
                "Sem título"
            ),
            "start": start_time,
            "end": end_time,
            "description": event.get(
                "description",
                ""
            )
        })

    return formatted_events

# Função para criar um evento no Google Calendar
def create_calendar_event(title, start_datetime, end_datetime, description=""):

    service = get_calendar_service()

    event = {
        "summary": title,
        "description": description,
        "start": {
            "dateTime": start_datetime,
            "timeZone": "America/Sao_Paulo",
        },
        "end": {
            "dateTime": end_datetime,
            "timeZone": "America/Sao_Paulo",
        },
    }

    created_event = (
        service.events()
        .insert(
            calendarId="primary",
            body=event
        )
        .execute()
    )

    return {
        "id": created_event.get("id"),
        "title": created_event.get("summary"),
        "start": created_event["start"].get("dateTime"),
        "end": created_event["end"].get("dateTime"),
        "link": created_event.get("htmlLink"),
    }