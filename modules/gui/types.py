from typing import TypedDict

from modules.context import Context

class RadioStruct(TypedDict):
    name    : str
    icon    : str
    flag    : int

class ToggleStruct(TypedDict):
    name    : str
    icon    : str

class CustomEvent( Context ):
    def __init__(self):
        self._queue : list = []

    def add(self, name: str, data=None):
        self._queue.append((name, data))

    def has(self, name: str) -> bool:
        """Return True if queue has given entry, Fales if not"""
        return any(event[0] == name for event in self._queue)

    def clear(self, name: str = None):
        """Clear given entry by rebuilding and excluding, no argument will clear entire queue"""
        if name is None: 
            self._queue.clear()

        else:
            self._queue = [e for e in self._queue if e[0] != name]

    def handle(self, name: str, func):
        """Call the given function if the event exists, then clear it automatically."""
        if self.has(name):
            func()
            self.clear(name)