from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class IncomingMessage:
    channel: str
    channel_user_id: str
    text: str
    session_id: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class OutgoingMessage:
    text: str
    channel: str
    channel_user_id: str
    metadata: dict = field(default_factory=dict)


class ChannelBase(ABC):
    name: str = "base"

    @abstractmethod
    async def start(self):
        ...

    @abstractmethod
    async def stop(self):
        ...

    @abstractmethod
    async def send_message(self, message: OutgoingMessage):
        ...
