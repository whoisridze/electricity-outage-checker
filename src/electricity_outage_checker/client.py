"""DTEK API client for fetching shutdown schedules."""

import json
import re
from datetime import datetime
from typing import Any

import httpx

from .models import (
    Address,
    DaySchedule,
    HourStatus,
    PowerStatus,
    ScheduleData,
    SchedulePreset,
)

SCHEDULE_PAGE_URL = "https://www.dtek-oem.com.ua/ua/shutdowns"
AJAX_URL = "https://www.dtek-oem.com.ua/ua/ajax"

# Pattern to extract CSRF token from page
CSRF_PATTERN = re.compile(r'name="_csrf-dtek-oem"[^>]*value="([^"]+)"')


class DTEKClientError(Exception):
    """Exception raised for DTEK API client errors."""


class DTEKClient:
    """Client for interacting with DTEK shutdown schedule API."""

    def __init__(self, timeout: float = 30.0) -> None:
        """Initialize the client.

        Args:
            timeout: Request timeout in seconds.
        """
        self._timeout = timeout
        self._client: httpx.Client | None = None
        self._csrf_token: str | None = None
        self._page_html: str | None = None

    def _get_client(self) -> httpx.Client:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                timeout=self._timeout,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    ),
                    "Accept": "application/json, text/html, */*",
                    "Accept-Language": "uk-UA,uk;q=0.9,en;q=0.8",
                },
            )
        return self._client

    def _fetch_page_and_csrf(self) -> str:
        """Fetch the schedule page and extract CSRF token.

        Returns:
            The page HTML content.

        Raises:
            DTEKClientError: If fetching fails.
        """
        if self._page_html is not None:
            return self._page_html

        client = self._get_client()

        try:
            response = client.get(SCHEDULE_PAGE_URL)
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise DTEKClientError(f"Failed to fetch schedule page: {e}") from e

        html = response.text
        self._page_html = html

        # Extract CSRF token
        csrf_match = CSRF_PATTERN.search(html)
        if csrf_match:
            self._csrf_token = csrf_match.group(1)

        return html

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None
        self._csrf_token = None
        self._page_html = None

    def __enter__(self) -> "DTEKClient":
        """Enter context manager."""
        return self

    def __exit__(self, *args: object) -> None:
        """Exit context manager."""
        self.close()

    def _extract_js_object(self, html: str, var_name: str) -> str:
        """Extract a JavaScript object from HTML by variable name.

        Uses brace counting to find the complete object, which is more
        reliable than regex for large nested objects.

        Args:
            html: HTML content to search.
            var_name: Variable name (e.g., "DisconSchedule.streets").

        Returns:
            The JavaScript object as a string.

        Raises:
            DTEKClientError: If the variable cannot be found.
        """
        # Find where the variable is assigned
        pattern = re.compile(rf"{re.escape(var_name)}\s*=\s*")
        match = pattern.search(html)
        if not match:
            raise DTEKClientError(f"Could not find {var_name} in page")

        start = match.end()

        # Find the opening brace
        if start >= len(html) or html[start] != "{":
            raise DTEKClientError(f"Expected object after {var_name}")

        # Count braces to find the end of the object
        depth = 0
        in_string = False
        escape_next = False
        end = start

        for i, char in enumerate(html[start:]):
            if escape_next:
                escape_next = False
                continue

            if char == "\\":
                escape_next = True
                continue

            if char == '"' and not escape_next:
                in_string = not in_string
                continue

            if in_string:
                continue

            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    end = start + i + 1
                    break

        if depth != 0:
            raise DTEKClientError(f"Unbalanced braces in {var_name}")

        return html[start:end]

    def _parse_js_object(self, js_code: str) -> Any:
        """Parse a JavaScript object literal to Python dict.

        Args:
            js_code: JavaScript object literal string.

        Returns:
            Parsed Python object.
        """
        # Handle escaped forward slashes (common in URLs in JS)
        cleaned = js_code.replace("\\/", "/")

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise DTEKClientError(f"Failed to parse JavaScript object: {e}") from e

    def fetch_schedule_page(self) -> tuple[dict[str, list[str]], SchedulePreset, ScheduleData]:
        """Fetch and parse the main schedule page.

        Returns:
            Tuple of (streets dict, preset data, schedule data).

        Raises:
            DTEKClientError: If fetching or parsing fails.
        """
        html = self._fetch_page_and_csrf()

        # Extract streets
        streets_js = self._extract_js_object(html, "DisconSchedule.streets")
        streets: dict[str, list[str]] = self._parse_js_object(streets_js)

        # Extract preset
        preset_js = self._extract_js_object(html, "DisconSchedule.preset")
        preset_raw = self._parse_js_object(preset_js)
        preset = SchedulePreset(
            days=preset_raw.get("days", {}),
            days_mini=preset_raw.get("days_mini", {}),
            schedule_names=preset_raw.get("sch_names", {}),
            time_zones=preset_raw.get("time_zone", {}),
            time_types=preset_raw.get("time_type", {}),
        )

        # Extract fact (actual schedule data)
        fact_js = self._extract_js_object(html, "DisconSchedule.fact")
        fact_raw = self._parse_js_object(fact_js)

        schedule = ScheduleData(
            data=fact_raw.get("data", {}),
            update_time=fact_raw.get("update", ""),
            today_timestamp=fact_raw.get("today", 0),
        )

        return streets, preset, schedule

    def fetch_address_group(self, city: str, street: str, house: str) -> str | None:
        """Fetch the power group for a specific address.

        Args:
            city: City/settlement name.
            street: Street name.
            house: House number.

        Returns:
            Power group ID (e.g., "GPV6.1") or None if not found.

        Raises:
            DTEKClientError: If the API request fails.
        """
        # Ensure we have session cookies and CSRF token
        self._fetch_page_and_csrf()

        client = self._get_client()

        # Build the form data in jQuery serializeArray format
        # The API expects data[0][name], data[0][value], data[1][name], etc.
        # Also requires _csrf-dtek-oem token for validation
        payload: dict[str, str] = {"method": "getHomeNum"}

        # Add CSRF token if available
        if self._csrf_token:
            payload["_csrf-dtek-oem"] = self._csrf_token

        form_fields = [
            ("city", city),
            ("street", street),
            ("house_num", house),
        ]
        for i, (name, value) in enumerate(form_fields):
            payload[f"data[{i}][name]"] = name
            payload[f"data[{i}][value]"] = value

        try:
            response = client.post(
                AJAX_URL,
                data=payload,
                headers={
                    "X-Requested-With": "XMLHttpRequest",
                    "Referer": SCHEDULE_PAGE_URL,
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise DTEKClientError(f"Failed to fetch address group: {e}") from e

        try:
            data = response.json()
        except ValueError as e:
            raise DTEKClientError(f"Invalid JSON response: {e}") from e

        if not data.get("result"):
            return None

        # Find the house in the response data
        house_data = data.get("data", {}).get(house)
        if house_data is None:
            return None

        # Get the power group from sub_type_reason
        groups: list[str] = house_data.get("sub_type_reason", [])
        if groups:
            return str(groups[0])  # Return the first group

        return None

    def fetch_houses(self, city: str, street: str) -> list[str]:
        """Fetch all available houses for a street.

        Args:
            city: City/settlement name.
            street: Street name.

        Returns:
            List of house numbers.

        Raises:
            DTEKClientError: If the API request fails.
        """
        # Ensure we have session cookies and CSRF token
        self._fetch_page_and_csrf()

        client = self._get_client()

        payload: dict[str, str] = {"method": "getHomeNum"}

        if self._csrf_token:
            payload["_csrf-dtek-oem"] = self._csrf_token

        form_fields = [
            ("city", city),
            ("street", street),
            ("house_num", ""),  # Empty to get all houses
        ]
        for i, (name, value) in enumerate(form_fields):
            payload[f"data[{i}][name]"] = name
            payload[f"data[{i}][value]"] = value

        try:
            response = client.post(
                AJAX_URL,
                data=payload,
                headers={
                    "X-Requested-With": "XMLHttpRequest",
                    "Referer": SCHEDULE_PAGE_URL,
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise DTEKClientError(f"Failed to fetch houses: {e}") from e

        try:
            data = response.json()
        except ValueError as e:
            raise DTEKClientError(f"Invalid JSON response: {e}") from e

        if not data.get("result"):
            return []

        # Return all house numbers from the data
        houses_data = data.get("data", {})
        return list(houses_data.keys())

    def get_schedule_for_address(self, address: Address) -> list[DaySchedule]:
        """Get the full schedule for an address.

        Args:
            address: Address to get schedule for.

        Returns:
            List of day schedules with power status for each hour.

        Raises:
            DTEKClientError: If fetching fails.
        """
        # Fetch the main schedule data (this also initializes the session)
        streets, preset, schedule_data = self.fetch_schedule_page()

        # Get the power group for this address
        group = self.fetch_address_group(address.city, address.street, address.house)
        if group is None:
            raise DTEKClientError(
                f"Could not find power group for address: {address.city}, "
                f"{address.street}, {address.house}"
            )

        # Build the schedule for each day
        result: list[DaySchedule] = []

        for timestamp_str, groups_data in schedule_data.data.items():
            timestamp = int(timestamp_str)
            date = datetime.fromtimestamp(timestamp)

            # Get the schedule for this group on this day
            group_schedule = groups_data.get(group, {})

            hours: list[HourStatus] = []
            for hour_str in map(str, range(1, 25)):
                status_key = group_schedule.get(hour_str, "yes")
                status = PowerStatus(status_key)

                # Get time range from preset
                time_info = preset.time_zones.get(hour_str, [f"{int(hour_str) - 1:02d}-{hour_str}"])
                time_range = time_info[0] if time_info else f"{int(hour_str) - 1:02d}-{hour_str}"

                hours.append(HourStatus(hour=int(hour_str), status=status, time_range=time_range))

            # Get day name
            day_num = str(date.isoweekday())
            day_name = preset.days.get(day_num, "")

            result.append(
                DaySchedule(
                    date=date,
                    day_name=day_name,
                    group=group,
                    hours=hours,
                )
            )

        # Sort by date
        result.sort(key=lambda d: d.date)

        return result
