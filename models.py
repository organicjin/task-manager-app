from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional


@dataclass
class Task:
    id: Optional[int] = None
    title: str = ""
    description: str = ""
    category: str = "업무"  # 업무 / 개인
    priority: str = "중간"  # 높음 / 중간 / 낮음
    urgency: str = "보통"  # 긴급 / 보통 / 여유
    quadrant: int = 4  # 아이젠하워 사분면 1~4
    project_id: Optional[int] = None
    due_date: Optional[date] = None
    status: str = "진행전"  # 진행전 / 진행중 / 완료
    created_at: Optional[datetime] = None

    @property
    def quadrant_label(self) -> str:
        labels = {
            1: "긴급 + 중요",
            2: "비긴급 + 중요",
            3: "긴급 + 비중요",
            4: "비긴급 + 비중요",
        }
        return labels.get(self.quadrant, "미분류")

    @property
    def days_left(self) -> Optional[int]:
        if self.due_date is None:
            return None
        return (self.due_date - date.today()).days


@dataclass
class Project:
    id: Optional[int] = None
    name: str = ""
    description: str = ""
    created_at: Optional[datetime] = None
