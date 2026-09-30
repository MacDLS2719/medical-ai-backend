import enum


class HealthPlaceKind(str, enum.Enum):
    hospital = "hospital"
    clinic = "clinic"
    pharmacy = "pharmacy"