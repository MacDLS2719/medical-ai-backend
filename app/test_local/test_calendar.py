import os
from dotenv import load_dotenv

# Load env file first
load_dotenv(".env")

from app.services.google_calendar_service import GoogleCalendarService
from datetime import datetime

try:
    print(f"GOOGLE_APPLICATION_CREDENTIALS: {os.getenv('GOOGLE_APPLICATION_CREDENTIALS')}")
    print(f"GOOGLE_CALENDAR_ID: {os.getenv('GOOGLE_CALENDAR_ID')}")
    service = GoogleCalendarService()
    event = service.create_event(
        summary="Test Meeting",
        start_datetime=datetime.now(),
        duration_minutes=30
    )
    print("Success!")
    print(event)
except Exception as e:
    import traceback
    traceback.print_exc()
