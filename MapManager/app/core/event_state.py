from threading import RLock

class EventState:
    _current_event: str | None = None
    _lock = RLock()

    @classmethod
    def set(cls, event_type: str | None):
        with cls._lock:
            cls._current_event = event_type

    @classmethod
    def get(cls) -> str | None:
        with cls._lock:
            return cls._current_event

    @classmethod
    def clear(cls):
        cls.set(None)

def set_current_event(event_type: str | None):
    EventState.set(event_type)

def get_current_event() -> str | None:
    return EventState.get()

def clear_current_event():
    EventState.clear()
