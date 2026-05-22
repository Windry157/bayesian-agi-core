from typing import Any, Dict, Optional


class StatePersistence:
    def __init__(self):
        self._state: Dict[str, Any] = {"knowledge": {"domains": []}}

    async def load_cognitive_state(self) -> Dict[str, Any]:
        return self._state

    async def update_state(self, state: Dict[str, Any]):
        self._state = state

    def get_state_summary(self) -> Dict[str, Any]:
        return self._state


state_persistence = StatePersistence()
