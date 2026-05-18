from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime
from app.models import PlanType

# ---------- Organization ----------
class OrganizationCreate(BaseModel):
    name: str
    email: EmailStr

class OrganizationOut(BaseModel):
    id: int
    name: str
    email: str
    plan: PlanType
    created_at: datetime
    is_active: bool

    model_config = ConfigDict(from_attributes=True)

# ---------- API Key ----------
class APIKeyCreate(BaseModel):
    name: Optional[str] = None

class APIKeyOut(BaseModel):
    id: int
    key_prefix: str
    name: Optional[str]
    created_at: datetime
    is_active: bool

    model_config = ConfigDict(from_attributes=True)

class APIKeyReveal(APIKeyOut):
    raw_key: str  # La clave sin hashear, solo se muestra una vez al crearla

# ---------- Template ----------
class TemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    html_content: str
    placeholders: Optional[str] = None  # JSON string con las variables esperadas

class TemplateOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    placeholders: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ---------- Document Generation ----------
class DocGenerateRequest(BaseModel):
    template_id: int
    data: dict  # JSON dinámico con los valores para la plantilla

class DocGenerateResponse(BaseModel):
    document_id: int
    pdf_url: Optional[str] = None
    message: str = "Documento generado exitosamente"

# ---------- Usage ----------
class UsageOut(BaseModel):
    organization_id: int
    year: int
    month: int
    documents_count: int

    model_config = ConfigDict(from_attributes=True)

# ---------- Respuesta genérica ----------
class MessageResponse(BaseModel):
    message: str