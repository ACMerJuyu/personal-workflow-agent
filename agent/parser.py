import re
from typing import Optional, Tuple


def extract_todo_id(message: str) -> Optional[int]:
    patterns = [
        r"todo\s*#?\s*(\d+)",
        r"task\s*#?\s*(\d+)",
        r"任务\s*#?\s*(\d+)",
        r"待办\s*#?\s*(\d+)",
        r"\b(\d+)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def extract_event_id(message: str) -> Optional[str]:
    match = re.search(r"event-\d+", message, re.IGNORECASE)
    if match:
        return match.group(0).lower()
    return None


def extract_time_range(message: str) -> Optional[Tuple[str, str]]:
    match = re.search(r"(\d{1,2}):(\d{2})\s*[-~到至]\s*(\d{1,2}):(\d{2})", message)
    if not match:
        return None

    start_hour, start_minute, end_hour, end_minute = match.groups()
    return (
        f"{int(start_hour):02d}:{start_minute}",
        f"{int(end_hour):02d}:{end_minute}",
    )

