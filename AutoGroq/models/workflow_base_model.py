
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

class WorkflowBaseModel:
    def __init__(
        self,
        name: str,
        description: str,
        agents: List[Dict],
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
        self.agents = [AgentBaseModel(**agent) for agent in agents] 
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
            "sender": {
                "type": self.sender.type,
                "config": self.sender.config,
                "timestamp": self.sender.timestamp,
                "user_id": self.sender.user_id,
                "tools": self.sender.tools,
            },
            "receiver": {
                "type": self.receiver.type,
                "config": self.receiver.config,
                "groupchat_config": self.receiver.groupchat_config,
                "timestamp": self.receiver.timestamp,
                "user_id": self.receiver.user_id,
                "tools": self.receiver.tools,
                "agents": [agent.to_dict() for agent in self.receiver.agents],
            },
            "type": self.type,
            "user_id": self.user_id,
            "timestamp": self.timestamp,
            "summary_method": self.summary_method,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict):
        sender = Sender(
            type=data["sender"]["type"],
            config=data["sender"]["config"],
            timestamp=data["sender"]["timestamp"],
            user_id=data["sender"]["user_id"],
            tools=data["sender"]["tools"],
        )
        receiver = Receiver(
            type=data["receiver"]["type"],
            config=data["receiver"]["config"],
            groupchat_config=data["receiver"]["groupchat_config"],
            timestamp=data["receiver"]["timestamp"],
            user_id=data["receiver"]["user_id"],
            tools=data["receiver"]["tools"],
            agents=[AgentBaseModel.from_dict(agent) for agent in data["receiver"].get("agents", [])],
        )
        return cls(
            id=data.get("id"),
            name=data["name"],
            description=data["description"],
            agents=data.get("agents", []),
            sender=sender,
            receiver=receiver,
            type=data["type"],
            user_id=data["user_id"],
            timestamp=data["timestamp"],
            summary_method=data["summary_method"],
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )