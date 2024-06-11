from typing import List, Dict, Optional
from datetime import datetime

class ProjectBaseModel:
    def __init__(
        self,
        re_engineered_prompt: str = "",
        deliverables: List[Dict] = None,
        id: Optional[int] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        user_id: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        due_date: Optional[str] = None,
        priority: Optional[str] = None,
        tags: Optional[List[str]] = None,
        attachments: Optional[List[str]] = None,
        notes: Optional[str] = None,
        collaborators: Optional[List[str]] = None,
        tools: Optional[List[Dict]] = None,
        workflows: Optional[List[Dict]] = None
    ):
        self.id = id or 1
        self.re_engineered_prompt = re_engineered_prompt
        self.deliverables = deliverables or []
        self.created_at = created_at or datetime.now().isoformat()
        self.updated_at = updated_at
        self.user_id = user_id or "user"
        self.name = name or "project"
        self.description = description
        self.status = status or "not started"
        self.due_date = due_date
        self.priority = priority
        self.tags = tags or []
        self.attachments = attachments or []
        self.notes = notes
        self.collaborators = collaborators or []
        self.tools = tools or []
        self.workflows = workflows or []


    def add_deliverable(self, deliverable: str):
        self.deliverables.append({"text": deliverable, "done": False})


    def mark_deliverable_done(self, index: int):
        if 0 <= index < len(self.deliverables):
            self.deliverables[index]["done"] = True


    def mark_deliverable_undone(self, index: int):
        if 0 <= index < len(self.deliverables):
            self.deliverables[index]["done"] = False


    def set_re_engineered_prompt(self, prompt: str):
        self.re_engineered_prompt = prompt

    def to_dict(self):
        return {
            "id": self.id,
            "re_engineered_prompt": self.re_engineered_prompt,
            "deliverables": self.deliverables,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "due_date": self.due_date,
            "priority": self.priority,
            "tags": self.tags,
            "attachments": self.attachments,
            "notes": self.notes,
            "collaborators": self.collaborators,
            "tools": self.tools,
            "workflows": self.workflows
        }

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(
            id=data.get("id"),
            re_engineered_prompt=data.get("re_engineered_prompt", ""),
            deliverables=data.get("deliverables", []),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            user_id=data.get("user_id"),
            name=data.get("name"),
            description=data.get("description"),
            status=data.get("status"),
            due_date=data.get("due_date"),
            priority=data.get("priority"),
            tags=data.get("tags"),
            attachments=data.get("attachments"),
            notes=data.get("notes"),
            collaborators=data.get("collaborators")
        )
    