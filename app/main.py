# ---------- IMPORTS ----------
import os
from alembic import command
from alembic.config import Config
from fastapi import FastAPI, Depends, HTTPException, Header, status
from fastapi.openapi.utils import get_openapi
from fastapi.responses import Response
from sqlalchemy.orm import Session
import json
from datetime import datetime, UTC

from app.database import get_db
from app import models, schemas, crud
from app.core.templates import generate_pdf_from_template_string

# ---------- CREACIÓN DE LA APP ----------
app = FastAPI(title="DocForge B2B API", version="1.0.0")

@app.on_event("startup")
def run_migrations():
    """Ejecuta las migraciones automáticamente al iniciar la aplicación."""
    try:
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        print("Migraciones ejecutadas correctamente.")
    except Exception as e:
        print(f"Error durante las migraciones: {e}")

# ---------- ESQUEMA DE SEGURIDAD PARA SWAGGER (BOTÓN AUTHORIZE) ----------
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key"
        }
    }
    openapi_schema["security"] = [{"ApiKeyAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# ---------- DEPENDENCIA DE AUTENTICACIÓN ----------
def get_current_organization(
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: Session = Depends(get_db)
) -> models.Organization:
    org = crud.get_organization_by_api_key(db, x_api_key)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key inválida o desactivada"
        )
    if not org.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organización desactivada")
    return org

# ---------- ENDPOINTS ----------

# Health check (para keep‑alive y monitoreo)
@app.get("/api/v1/health")
def health_check():
    return {"status": "ok"}

# Registro de organización (abierto, sin auth)
@app.post("/api/v1/organizations", response_model=schemas.OrganizationOut, status_code=201)
def register_organization(org: schemas.OrganizationCreate, db: Session = Depends(get_db)):
    existing = crud.get_organization_by_email(db, org.email)
    if existing:
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    return crud.create_organization(db, org)

# Gestión de API Keys (autenticado como organización)
@app.post("/api/v1/api-keys", response_model=schemas.APIKeyReveal, status_code=201)
def create_api_key(
    key_data: schemas.APIKeyCreate = None,
    org: models.Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    if key_data is None:
        key_data = schemas.APIKeyCreate()
    db_key, raw_key = crud.create_api_key(db, org.id, key_data.name)
    return schemas.APIKeyReveal(
        id=db_key.id,
        key_prefix=db_key.key_prefix,
        name=db_key.name,
        created_at=db_key.created_at,
        is_active=db_key.is_active,
        raw_key=raw_key
    )

# Plantillas (CRUD)
@app.post("/api/v1/templates", response_model=schemas.TemplateOut, status_code=201)
def create_template(
    template: schemas.TemplateCreate,
    org: models.Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    return crud.create_template(db, org.id, template)

@app.get("/api/v1/templates", response_model=list[schemas.TemplateOut])
def list_templates(
    org: models.Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    return crud.get_templates_by_org(db, org.id)

@app.get("/api/v1/templates/{template_id}", response_model=schemas.TemplateOut)
def get_template(
    template_id: int,
    org: models.Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    tpl = crud.get_template_by_id_and_org(db, template_id, org.id)
    if not tpl:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    return tpl

# Generación de documentos (el corazón del SaaS)
@app.post("/api/v1/documents/generate", response_class=Response)
async def generate_document(
    payload: schemas.DocGenerateRequest,
    org: models.Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    # Verificar que la plantilla pertenece a la organización
    template = crud.get_template_by_id_and_org(db, payload.template_id, org.id)
    if not template:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")

    # Verificar límite de documentos del plan
    if not crud.check_and_increment_usage(db, org):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Límite mensual de documentos alcanzado. Actualiza tu plan."
        )

    try:
        pdf_bytes = await generate_pdf_from_template_string(template.html_content, payload.data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar PDF: {str(e)}")

    # Registrar el documento en la base de datos
    doc = crud.create_document(
        db,
        org_id=org.id,
        template_id=template.id,
        data_json=json.dumps(payload.data)
    )

    # Devolver PDF con nombre descriptivo
    headers = {"Content-Disposition": f"attachment; filename=documento-{doc.id}.pdf"}
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)

# Estado del plan
@app.get("/api/v1/me/plan")
def get_my_plan(
    org: models.Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    now = datetime.now(UTC)
    usage = db.query(models.Usage).filter(
        models.Usage.organization_id == org.id,
        models.Usage.year == now.year,
        models.Usage.month == now.month
    ).first()
    return {
        "organization": org.name,
        "plan": org.plan.value,
        "current_month_documents": usage.documents_count if usage else 0,
        "limit": 50 if org.plan == models.PlanType.FREE else "ilimitado"
    }