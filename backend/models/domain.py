from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Repository:
    id: str
    name: str
    path: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class AnalysisTask:
    id: str
    repo_id: str
    query: str
    status: str = "pending"
    progress: int = 0
    report: str = ""
