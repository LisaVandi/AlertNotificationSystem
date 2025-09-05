from threading import RLock
import time

class EventState:
    _current_event: str | None = None
    _updated_at: float = 0.0
    _lock = RLock()

    @classmethod
    def set(cls, event_type: str | None):
        with cls._lock:
            cls._current_event = event_type
            cls._updated_at = time.monotonic()

    @classmethod
    def get(cls) -> str | None:
        with cls._lock:
            return cls._current_event

    @classmethod
    def age_seconds(cls) -> float:
        with cls._lock:
            return (time.monotonic() - cls._updated_at) if cls._updated_at else float("inf")

    @classmethod
    def clear(cls):
        with cls._lock:
            cls._current_event = None
            cls._updated_at = 0.0

def set_current_event(event_type: str | None): EventState.set(event_type)
def get_current_event() -> str | None: return EventState.get()
def clear_current_event(): EventState.clear()
