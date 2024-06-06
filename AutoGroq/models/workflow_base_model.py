
from agent_base_model import AgentBaseModel
from typing import List, Dict, Optional

class WorkflowBaseModel:
    def __init__(
        self,
        name: str,
        description: str,
        agents: List[Dict],
        settings: Dict,
        id: Optional[int] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        user_id: Optional[str] = None,
        type: Optional[str] = None,
        summary_method: Optional[str] = None,
        sender: Optional[Dict] = None,
        receiver: Optional[Dict] = None,
        groupchat_config: Optional[Dict] = None,
        timestamp: Optional[str] = None
    ):
        self.id = id
        self.name = name
        self.description = description
        self.agents = [AgentBaseModel(**agent) for agent in agents]  # List of AgentBaseModel instances
        self.settings = settings  # Dict containing workflow-specific settings
        self.created_at = created_at
        self.updated_at = updated_at
        self.user_id = user_id
        self.type = type
        self.summary_method = summary_method
        self.sender = sender
        self.receiver = receiver
        self.groupchat_config = groupchat_config
        self.timestamp = timestamp

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "agents": [agent.to_dict() for agent in self.agents],
            "settings": self.settings,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "user_id": self.user_id,
            "type": self.type,
            "summary_method": self.summary_method,
            "sender": self.sender,
            "receiver": self.receiver,
            "groupchat_config": self.groupchat_config,
            "timestamp": self.timestamp
        }

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(
            id=data.get("id"),
            name=data["name"],
            description=data["description"],
            agents=data["agents"],
            settings=data["settings"],
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            user_id=data.get("user_id"),
            type=data.get("type"),
            summary_method=data.get("summary_method"),
            sender=data.get("sender"),
            receiver=data.get("receiver"),
            groupchat_config=data.get("groupchat_config"),
            timestamp=data.get("timestamp")
        )
    