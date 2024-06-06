
from skill_base_model import SkillBaseModel
from typing import List, Dict, Optional

class AgentBaseModel:
    def __init__(
        self,
        name: str,
        description: str,
        skills: List[Dict],
        config: Dict,
        id: Optional[int] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        user_id: Optional[str] = None,
        workflows: Optional[str] = None,
        type: Optional[str] = None,
        models: Optional[List[Dict]] = None,
        verbose: Optional[bool] = None,
        allow_delegation: Optional[bool] = None,
        new_description: Optional[str] = None,
        timestamp: Optional[str] = None,
        tools: Optional[List[str]] = None
    ):
        self.id = id
        self.name = name
        self.description = description
        self.skills = [SkillBaseModel(**skill) for skill in skills]  # List of SkillBaseModel instances
        self.config = config  # Dict containing agent-specific configurations
        self.created_at = created_at
        self.updated_at = updated_at
        self.user_id = user_id
        self.workflows = workflows
        self.type = type
        self.models = models
        self.verbose = verbose
        self.allow_delegation = allow_delegation
        self.new_description = new_description
        self.timestamp = timestamp
        self.tools = tools

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "skills": [skill.to_dict() for skill in self.skills],
            "config": self.config,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "user_id": self.user_id,
            "workflows": self.workflows,
            "type": self.type,
            "models": self.models,
            "verbose": self.verbose,
            "allow_delegation": self.allow_delegation,
            "new_description": self.new_description,
            "timestamp": self.timestamp,
            "tools": self.tools
        }

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(
            id=data.get("id"),
            name=data["name"],
            description=data["description"],
            skills=data["skills"],
            config=data["config"],
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            user_id=data.get("user_id"),
            workflows=data.get("workflows"),
            type=data.get("type"),
            models=data.get("models"),
            verbose=data.get("verbose"),
            allow_delegation=data.get("allow_delegation"),
            new_description=data.get("new_description"),
            timestamp=data.get("timestamp"),
            tools=data.get("tools")
        )
    