"""Data models for shutdown schedules."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class PowerStatus(Enum):
    """Power availability status for a time slot."""

    YES = "yes"  # Power is available
    NO = "no"  # Power is off (scheduled outage)
    MAYBE = "maybe"  # Possible outage
    FIRST = "first"  # No power for first 30 minutes of the hour
    SECOND = "second"  # No power for second 30 minutes of the hour
    MAYBE_FIRST = "mfirst"  # Possible no power for first 30 minutes
    MAYBE_SECOND = "msecond"  # Possible no power for second 30 minutes

    @property
    def has_power(self) -> bool:
        """Check if power is definitely available."""
        return self == PowerStatus.YES

    @property
    def no_power(self) -> bool:
        """Check if power is definitely off."""
        return self == PowerStatus.NO

    @property
    def is_partial(self) -> bool:
        """Check if this is a partial outage (30 min)."""
        return self in (
            PowerStatus.FIRST,
            PowerStatus.SECOND,
            PowerStatus.MAYBE_FIRST,
            PowerStatus.MAYBE_SECOND,
        )

    @property
    def is_uncertain(self) -> bool:
        """Check if the status is uncertain (maybe)."""
        return self in (PowerStatus.MAYBE, PowerStatus.MAYBE_FIRST, PowerStatus.MAYBE_SECOND)

    def get_display_text(self, translations: dict[str, str] | None = None) -> str:
        """Get human-readable display text.

        Args:
            translations: Optional translation dict from preset.

        Returns:
            Human-readable status text.
        """
        if translations and self.value in translations:
            return translations[self.value]

        defaults = {
            "yes": "Power ON",
            "no": "Power OFF",
            "maybe": "Maybe OFF",
            "first": "OFF first 30 min",
            "second": "OFF second 30 min",
            "mfirst": "Maybe OFF first 30 min",
            "msecond": "Maybe OFF second 30 min",
        }
        return defaults.get(self.value, self.value)


@dataclass
class Address:
    """Represents a physical address for schedule lookup."""

    city: str  # City/settlement name
    street: str  # Street name
    house: str  # House number

    def __str__(self) -> str:
        """Return formatted address string."""
        return f"{self.city}, {self.street}, {self.house}"

    @classmethod
    def from_string(cls, address_str: str) -> "Address":
        """Parse address from a comma-separated string.

        Args:
            address_str: Address in format "city, street, house".

        Returns:
            Parsed Address object.

        Raises:
            ValueError: If address format is invalid.
        """
        parts = [p.strip() for p in address_str.split(",")]
        if len(parts) != 3:
            raise ValueError(
                f"Invalid address format: '{address_str}'. Expected format: 'city, street, house'"
            )
        return cls(city=parts[0], street=parts[1], house=parts[2])


@dataclass
class HourStatus:
    """Power status for a specific hour."""

    hour: int  # Hour number (1-24)
    status: PowerStatus
    time_range: str  # Display string like "08-09"

    @property
    def start_time(self) -> str:
        """Get the start time of this hour slot."""
        return f"{self.hour - 1:02d}:00"

    @property
    def end_time(self) -> str:
        """Get the end time of this hour slot."""
        return f"{self.hour:02d}:00" if self.hour < 24 else "24:00"


@dataclass
class DaySchedule:
    """Schedule for a single day."""

    date: datetime
    day_name: str  # Ukrainian day name
    group: str  # Power group (e.g., "GPV6.1")
    hours: list[HourStatus]

    @property
    def date_str(self) -> str:
        """Get formatted date string."""
        return self.date.strftime("%d.%m.%Y")

    def get_outage_periods(self) -> list[tuple[str, str, PowerStatus]]:
        """Get list of outage periods.

        Returns:
            List of (start_time, end_time, status) tuples for periods without power.
        """
        periods: list[tuple[str, str, PowerStatus]] = []
        current_start: str | None = None
        current_status: PowerStatus | None = None

        for hour in self.hours:
            if not hour.status.has_power:
                if current_start is None:
                    current_start = hour.start_time
                    current_status = hour.status
            elif current_start is not None and current_status is not None:
                # End of outage period
                prev_hour = self.hours[hour.hour - 2] if hour.hour > 1 else hour
                periods.append((current_start, prev_hour.end_time, current_status))
                current_start = None
                current_status = None

        # Handle case where outage extends to end of day
        if current_start is not None and current_status is not None:
            periods.append((current_start, "24:00", current_status))

        return periods


@dataclass
class SchedulePreset:
    """Preset configuration from the DTEK page."""

    days: dict[str, str]  # Day number to name mapping
    days_mini: dict[str, str]  # Day number to short name mapping
    schedule_names: dict[str, str]  # Group ID to display name mapping
    time_zones: dict[str, list[str]]  # Hour to time info mapping
    time_types: dict[str, str]  # Status to display text mapping


@dataclass
class ScheduleData:
    """Raw schedule data from the DTEK page."""

    data: dict[str, dict[str, dict[str, str]]]  # timestamp -> group -> hour -> status
    update_time: str  # Last update time string
    today_timestamp: int  # Today's date as Unix timestamp

    def get_available_dates(self) -> list[datetime]:
        """Get list of available dates in the schedule."""
        dates = []
        for timestamp_str in self.data:
            timestamp = int(timestamp_str)
            dates.append(datetime.fromtimestamp(timestamp))
        return sorted(dates)

    def get_schedule_for_group(self, group: str, timestamp: int) -> dict[str, str]:
        """Get schedule for a specific group and day.

        Args:
            group: Power group ID (e.g., "GPV6.1").
            timestamp: Unix timestamp for the day.

        Returns:
            Hour to status mapping.
        """
        day_data = self.data.get(str(timestamp), {})
        return day_data.get(group, {})
