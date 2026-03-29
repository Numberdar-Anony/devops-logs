from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Integer, JSON, String, Text, func, ForeignKey, Float
from sqlalchemy.orm import relationship
from app.db.base import Base


class LogRecord(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(50), index=True)
    service = Column(String(100), index=True)
    level = Column(String(50), nullable=True)
    message = Column(String(512), nullable=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    raw = Column(JSON, nullable=False)


class Finding(Base):
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, index=True)
    plugin_name = Column(String(100), index=True)
    summary = Column(String(512))
    details = Column(Text)
    severity = Column(String(50), default="medium")
    source = Column(String(50), index=True)
    correlation_id = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, index=True)
    root_cause = Column(Text)
    impact = Column(Text)
    fix = Column(Text)
    correlation_id = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# New normalized persistence


class PersistedAnalysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(String(64), unique=True, index=True)
    source = Column(String(50))
    severity = Column(String(32))
    summary = Column(Text)
    root_cause = Column(Text)
    recommendation = Column(Text)
    raw_response_json = Column(JSON)
    raw_logs = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    findings = relationship("PersistedFinding", back_populates="analysis", cascade="all, delete-orphan")
    resources = relationship("PersistedResource", back_populates="analysis", cascade="all, delete-orphan")


class PersistedFinding(Base):
    __tablename__ = "analysis_findings"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id", ondelete="CASCADE"))
    plugin = Column(String(64))
    title = Column(String(256))
    severity = Column(String(32))
    description = Column(Text)
    line_number = Column(Integer, nullable=True)

    analysis = relationship("PersistedAnalysis", back_populates="findings")


class PersistedResource(Base):
    __tablename__ = "affected_resources"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id", ondelete="CASCADE"))
    name = Column(String(128))
    type = Column(String(64))
    risk = Column(Float)
    plugin = Column(String(64))

    analysis = relationship("PersistedAnalysis", back_populates="resources")
