from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from backend.db.database import Base


class RepoModel(Base):
    __tablename__ = "repos"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    path = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TaskModel(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True)
    repo_id = Column(String, nullable=False)
    query = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="pending")
    progress = Column(Integer, nullable=False, default=0)
    report = Column(Text, nullable=False, default="")
