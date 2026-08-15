from abc import ABC, abstractmethod
from typing import Dict, Any

from app.ai.models import NormalizedDocument


class BaseAdapter(ABC):
    """Base class for all document format adapters."""

    def __init__(self, document_id: str, user_id: str, file_path: str, mime_type: str, title: str):
        self.document_id = document_id
        self.user_id = user_id
        self.file_path = file_path
        self.mime_type = mime_type
        self.title = title

    @abstractmethod
    def parse(self, file_bytes: bytes) -> NormalizedDocument:
        """Parses the raw file bytes into a NormalizedDocument."""
        pass
