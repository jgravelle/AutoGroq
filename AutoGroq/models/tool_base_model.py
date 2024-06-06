
from typing import List, Dict, Optional

class ToolBaseModel:
    def __init__(
        self,
        name: str,
        description: str,
        id: Optional[int] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        user_id: Optional[str] = None,
        content: Optional[str] = None,
        secrets: Optional[Dict] = None,
        libraries: Optional[List[str]] = None,
        file_name: Optional[str] = None,
        timestamp: Optional[str] = None,
        title: Optional[str] = None
    ):
        self.id = id
        self.name = name
        self.description = description
        self.created_at = created_at
        self.updated_at = updated_at
        self.user_id = user_id
        self.content = content
        self.secrets = secrets
        self.libraries = libraries
        self.file_name = file_name
        self.timestamp = timestamp
        self.title = title

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "user_id": self.user_id,
            "content": self.content,
            "secrets": self.secrets,
            "libraries": self.libraries,
            "file_name": self.file_name,
            "timestamp": self.timestamp,
            "title": self.title
        }

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(
            id=data.get("id"),
            name=data["name"],
            description=data["description"],
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            user_id=data.get("user_id"),
            content=data.get("content"),
            secrets=data.get("secrets"),
            libraries=data.get("libraries"),
            file_name=data.get("file_name"),
            timestamp=data.get("timestamp"),
            title=data.get("title")
        )
    