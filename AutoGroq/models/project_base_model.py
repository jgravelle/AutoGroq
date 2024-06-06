
from typing import List, Dict, Optional

class ProjectBaseModel:
    def __init__(
        self,
        re_engineered_prompt: str = "",
        objectives: List[Dict] = None,
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
        collaborators: Optional[List[str]] = None
    ):
        self.id = id
        self.re_engineered_prompt = re_engineered_prompt
        self.objectives = objectives or []
        self.deliverables = deliverables or []
        self.created_at = created_at
        self.updated_at = updated_at
        self.user_id = user_id
        self.name = name
        self.description = description
        self.status = status
        self.due_date = due_date
        self.priority = priority
        self.tags = tags
        self.attachments = attachments
        self.notes = notes
        self.collaborators = collaborators

    def add_deliverable(self, deliverable: str):
        self.deliverables.append({"text": deliverable, "done": False})

    def add_objective(self, objective: str):
        self.objectives.append({"text": objective, "done": False})

    def mark_deliverable_done(self, index: int):
        if 0 <= index < len(self.deliverables):
            self.deliverables[index]["done"] = True

    def mark_deliverable_undone(self, index: int):
        if 0 <= index < len(self.deliverables):
            self.deliverables[index]["done"] = False

    def mark_objective_done(self, index: int):
        if 0 <= index < len(self.objectives):
            self.objectives[index]["done"] = True

    def mark_objective_undone(self, index: int):
        if 0 <= index < len(self.objectives):
            self.objectives[index]["done"] = False

    def set_re_engineered_prompt(self, prompt: str):
        self.re_engineered_prompt = prompt

    def to_dict(self):
        return {
            "id": self.id,
            "re_engineered_prompt": self.re_engineered_prompt,
            "objectives": self.objectives,
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
            "collaborators": self.collaborators
        }

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(
            id=data.get("id"),
            re_engineered_prompt=data.get("re_engineered_prompt", ""),
            objectives=data.get("objectives", []),
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
    