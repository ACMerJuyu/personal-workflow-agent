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
class AgentResult:
    title: str
    bullets: List[str]
    trace: List[ToolCall] = field(default_factory=list)

    def to_text(self) -> str:
        lines = [self.title]
        lines.extend(f"{index + 1}. {bullet}" for index, bullet in enumerate(self.bullets))
        return "\n".join(lines)

