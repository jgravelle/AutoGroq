
from typing import List, Dict, Optional

class ToolBaseModel:
    def __init__(
        self,
        name: str,
        description: str,
        title: str,
        file_name: str,
        content: str,
        id: Optional[int] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        user_id: Optional[str] = None,
        secrets: Optional[Dict] = None, # Optional[Dict] means it can be a dictionary or None
        libraries: Optional[List[str]] = None,
        timestamp: Optional[str] = None
    ):
        self.id = id
        self.name = name
        self.description = description
        self.title = title
        self.file_name = file_name
        self.content = content
        self.created_at = created_at
        self.updated_at = updated_at
        self.user_id = user_id
        self.secrets = secrets
        self.libraries = libraries
        self.timestamp = timestamp

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "title": self.title,
            "file_name": self.file_name,
            "content": self.content,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "user_id": self.user_id,
            "secrets": self.secrets,
            "libraries": self.libraries,
            "timestamp": self.timestamp
        }

    @classmethod
    def from_dict(cls, data: Dict):     
        return cls(
            id=data.get("id"),
            name=data.get("name", ""),  # Default to empty string if 'name' is missing
            description=data.get("description", ""),  # Default to empty string if 'description' is missing
            title=data["title"],
            file_name=data["file_name"],
            content=data["content"],
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            user_id=data.get("user_id"),
            secrets=data.get("secrets"),
            libraries=data.get("libraries"),
            timestamp=data.get("timestamp")
        )
    