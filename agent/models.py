from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ToolCall:
    name: str
    arguments: Dict[str, Any]
    result: Any

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "arguments": self.arguments,
            "result": self.result,
        }


@dataclass
class ReActStep:
    kind: str
    content: str
    tool_name: str = ""
    arguments: Dict[str, Any] = field(default_factory=dict)
    observation: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "content": self.content,
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "observation": self.observation,
        }


@dataclass
class AgentResult:
    title: str
    bullets: List[str]
    trace: List[ToolCall] = field(default_factory=list)
    react_steps: List[ReActStep] = field(default_factory=list)

    def to_text(self) -> str:
        lines = [self.title]
        lines.extend(f"{index + 1}. {bullet}" for index, bullet in enumerate(self.bullets))
        return "\n".join(lines)
