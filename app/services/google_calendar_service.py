import os
from datetime import datetime, timedelta
from typing import Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build


class GoogleCalendarService:
    SCOPES = [
        "https://www.googleapis.com/auth/calendar"
    ]

    def __init__(self):
        credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        calendar_id = os.getenv("GOOGLE_CALENDAR_ID")

        if not credentials_path:
            raise ValueError(
                "GOOGLE_APPLICATION_CREDENTIALS no está configurado."
            )

        if not calendar_id:
            raise ValueError(
                "GOOGLE_CALENDAR_ID no está configurado."
            )

        if not os.path.exists(credentials_path):
            raise FileNotFoundError(
                f"No se encontró el archivo de credenciales: {credentials_path}"
            )

        self.calendar_id = calendar_id

        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=self.SCOPES,
        )

        self.service = build(
            "calendar",
            "v3",
            credentials=credentials,
        )

    def create_event(
        self,
        summary: str,
        start_datetime: datetime,
        duration_minutes: int = 30,
        description: Optional[str] = None,
        attendees: Optional[list[str]] = None,
    ) -> dict:
        """
        Crea un evento en Google Calendar y genera una reunión de Google Meet.
        """

        end_datetime = start_datetime + timedelta(
            minutes=duration_minutes
        )

        event = {
            "summary": summary,
            "description": description or "",
            "start": {
                "dateTime": start_datetime.isoformat(),
                "timeZone": "America/Bogota",
            },
            "end": {
                "dateTime": end_datetime.isoformat(),
                "timeZone": "America/Bogota",
            },
            "conferenceData": {
                "createRequest": {
                    "requestId": (
                        f"medical-ai-{int(datetime.now().timestamp())}"
                    ),
                    "conferenceSolutionKey": {
                        "type": "hangoutsMeet"
                    },
                }
            },
        }

        if attendees:
            event["attendees"] = [
                {"email": email}
                for email in attendees
            ]

        created_event = (
            self.service.events()
            .insert(
                calendarId=self.calendar_id,
                body=event,
                conferenceDataVersion=1,
                sendUpdates="all",
            )
            .execute()
        )

        meet_url = self._extract_meet_url(created_event)

        return {
            "event_id": created_event.get("id"),
            "calendar_url": created_event.get("htmlLink"),
            "meet_url": meet_url,
            "summary": created_event.get("summary"),
            "start": created_event.get("start"),
            "end": created_event.get("end"),
        }

    def get_event(self, event_id: str) -> Optional[dict]:
        try:
            return (
                self.service.events()
                .get(
                    calendarId=self.calendar_id,
                    eventId=event_id,
                )
                .execute()
            )
        except Exception:
            return None

    def delete_event(self, event_id: str) -> bool:
        try:
            (
                self.service.events()
                .delete(
                    calendarId=self.calendar_id,
                    eventId=event_id,
                )
                .execute()
            )

            return True

        except Exception:
            return False

    def _extract_meet_url(self, event: dict) -> Optional[str]:
        conference_data = event.get("conferenceData")

        if not conference_data:
            return None

        entry_points = conference_data.get("entryPoints", [])

        for entry_point in entry_points:
            if entry_point.get("entryPointType") == "video":
                return entry_point.get("uri")

        return None