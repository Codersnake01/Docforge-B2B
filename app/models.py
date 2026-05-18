from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Text, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database import Base

class PlanType(str, enum.Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    plan = Column(Enum(PlanType), default=PlanType.FREE, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    api_keys = relationship("APIKey", back_populates="organization", cascade="all, delete-orphan")
    templates = relationship("Template", back_populates="organization", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="organization", cascade="all, delete-orphan")

class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    key_prefix = Column(String(8), unique=True, nullable=False)  # para identificar
    hashed_key = Column(String, nullable=False)                  # hash seguro
    name = Column(String, nullable=True)  # ej: "Producción"
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)

    organization = relationship("Organization", back_populates="api_keys")

class Template(Base):
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    html_content = Column(Text, nullable=False)  # La plantilla Jinja2/HTML
    placeholders = Column(Text, nullable=True)   # JSON con los nombres de variables esperadas
    created_at = Column(DateTime, default=datetime.utcnow)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)

    organization = relationship("Organization", back_populates="templates")

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("templates.id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    data_json = Column(Text, nullable=True)       # JSON usado para la generación (opcional)
    pdf_url = Column(String, nullable=True)       # en el futuro podrías almacenar en S3
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="documents")
    template = relationship("Template")

class Usage(Base):
    __tablename__ = "usage"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    documents_count = Column(Integer, default=0)

    # Restricción única para evitar duplicados por organización y mes
    __table_args__ = (
        UniqueConstraint('organization_id', 'year', 'month', name='_org_month_uc'),
    )