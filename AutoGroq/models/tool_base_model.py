# tool_base_model.py

from typing import List, Dict, Optional, Callable

class ToolBaseModel:
    def __init__(
        self,
        name: str,
        description: str,
        title: str,
        file_name: str,
        content: str,
        function: Optional[Callable] = None,
        id: Optional[int] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        user_id: Optional[str] = None,
        secrets: Optional[Dict] = None,
        libraries: Optional[List[str]] = None,
        timestamp: Optional[str] = None
    ):
        self.id = id
        self.name = name
        self.description = description
        self.title = title
        self.file_name = file_name
        self.content = content
        self.function = function
        self.created_at = created_at
        self.updated_at = updated_at
        self.user_id = user_id
        self.secrets = secrets if secrets is not None else []
        self.libraries = libraries if libraries is not None else []
        self.timestamp = timestamp

    def execute(self, *args, **kwargs):
        if self.function:
            return self.function(*args, **kwargs)
        else:
            raise ValueError(f"No function defined for tool {self.name}")

    def __str__(self):
        return f"{self.name}: {self.description}"

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "title": self.title,
            "file_name": self.file_name,
            "content": self.content,
            "id": self.id,
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
    
    def get(self, key, default=None):
        return getattr(self, key, default)

    def __getitem__(self, key):
        return getattr(self, key)

    def __contains__(self, key):
        return hasattr(self, key)
    