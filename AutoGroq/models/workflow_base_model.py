from typing import List, Dict, Optional
from models.agent_base_model import AgentBaseModel

class Sender:
    def __init__(
        self,
        type: str,
        config: Dict,
        timestamp: str,
        user_id: str,
        tools: List[Dict],
    ):
        self.type = type
        self.config = config
        self.timestamp = timestamp
        self.user_id = user_id
        self.tools = tools

    def to_dict(self):
        return {
            "type": self.type,
            "config": self.config,
            "timestamp": self.timestamp,
            "user_id": self.user_id,
            "tools": self.tools,
        }

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(
            type=data["type"],
            config=data["config"],
            timestamp=data["timestamp"],
            user_id=data["user_id"],
            tools=data["tools"],
        )

class Receiver:
    def __init__(
        self,
        type: str,
        config: Dict,
        groupchat_config: Dict,
        timestamp: str,
        user_id: str,
        tools: List[Dict],
        agents: List[AgentBaseModel],
    ):
        self.type = type
        self.config = config
        self.groupchat_config = groupchat_config
        self.timestamp = timestamp
        self.user_id = user_id
        self.tools = tools
        self.agents = agents

    def to_dict(self):
        return {
            "type": self.type,
            "config": self.config,
            "groupchat_config": self.groupchat_config,
            "timestamp": self.timestamp,
            "user_id": self.user_id,
            "tools": self.tools,
            "agents": [agent.to_dict() for agent in self.agents],
        }

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(
            type=data["type"],
            config=data["config"],
            groupchat_config=data["groupchat_config"],
            timestamp=data["timestamp"],
            user_id=data["user_id"],
            tools=data["tools"],
            agents=[AgentBaseModel.from_dict(agent) for agent in data.get("agents", [])],
        )

class WorkflowBaseModel:
    def __init__(
        self,
        name: str,
        description: str,
        agents: List[AgentBaseModel],
        sender: Sender,
        receiver: Receiver,
        type: str,
        user_id: str,
        timestamp: str,
        summary_method: str,
        settings: Dict = None,
        groupchat_config: Dict = None,
        id: Optional[int] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
    ):
        self.id = id
        self.name = name
        self.description = description
        self.agents = agents
        self.sender = sender
        self.receiver = receiver
        self.type = type
        self.user_id = user_id
        self.timestamp = timestamp
        self.summary_method = summary_method
        self.settings = settings or {}
        self.groupchat_config = groupchat_config or {}
        self.created_at = created_at
        self.updated_at = updated_at

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "agents": [agent.to_dict() for agent in self.agents],
            "sender": self.sender.to_dict(),
            "receiver": self.receiver.to_dict(),
            "type": self.type,
            "user_id": self.user_id,
            "timestamp": self.timestamp,
            "summary_method": self.summary_method,
            "settings": self.settings,
            "groupchat_config": self.groupchat_config,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict):
        sender = Sender.from_dict(data["sender"])
        receiver = Receiver.from_dict(data["receiver"])
        return cls(
            id=data.get("id"),
            name=data["name"],
            description=data["description"],
            agents=[AgentBaseModel.from_dict(agent) for agent in data.get("agents", [])],
            sender=sender,
            receiver=receiver,
            type=data["type"],
            user_id=data["user_id"],
            timestamp=data["timestamp"],
            summary_method=data["summary_method"],
            settings=data.get("settings", {}),
            groupchat_config=data.get("groupchat_config", {}),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )