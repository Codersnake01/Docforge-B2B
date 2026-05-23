# ---------- IMPORTS ----------
from fastapi import FastAPI, Depends, HTTPException, Header, status, Request
from fastapi.openapi.utils import get_openapi
from fastapi.responses import Response
from sqlalchemy.orm import Session
import json
from datetime import datetime, UTC
import hashlib
import hmac
import os
import requests
from app.database import get_db, engine, Base
from app import models, schemas, crud
from app.core.templates import generate_pdf_from_template_string



# ---------- CREACIÓN DE LA APP ----------
app = FastAPI(title="DocForge B2B API", version="1.0.0")




@app.on_event("startup")
def create_tables():
    Base.metadata.create_all(bind=engine)
    print("✅ Tablas verificadas/creadas exitosamente.")



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
    "limit": 50 if org.plan == models.PlanType.FREE else (5000 if org.plan == models.PlanType.PRO else "ilimitado")
}



# ---------- WEBHOOK DE POLAR ----------

POLAR_WEBHOOK_SECRET = os.getenv("POLAR_WEBHOOK_SECRET", "")

@app.post("/api/v1/webhooks/polar")
async def polar_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """Recibe eventos de suscripción de Polar y actualiza el plan de la organización."""
    body = await request.body()
    signature = request.headers.get("polar-signature", "")

    # Verificar firma del webhook
    expected_signature = hmac.new(
        POLAR_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=403, detail="Firma inválida")

    payload = json.loads(body)
    event_type = payload.get("type", "")

    # Solo nos interesa cuando se crea o actualiza una suscripción
    if event_type in ("subscription.created", "subscription.updated"):
        customer_email = payload["data"]["customer"]["email"]
        product_name = payload["data"]["product"]["name"]

        # Mapear nombre de producto a plan
        if "PRO" in product_name:
            new_plan = models.PlanType.PRO
        elif "ENTERPRISE" in product_name:
            new_plan = models.PlanType.ENTERPRISE
        else:
            new_plan = models.PlanType.FREE

        # Buscar la organización por email y actualizarle el plan
        org = crud.get_organization_by_email(db, customer_email)
        if org:
            org.plan = new_plan
            db.commit()
            print(f"✅ Plan de {org.name} actualizado a {new_plan.value}")

    return {"status": "ok"}



# ---------- SINCRONIZACIÓN DE PLANES CON POLAR ----------
POLAR_ACCESS_TOKEN = os.getenv("POLAR_ACCESS_TOKEN", "")

@app.get("/api/v1/sync-subscriptions")
def sync_subscriptions(db: Session = Depends(get_db)):
    """Consulta las suscripciones activas en Polar y actualiza los planes de las organizaciones."""
    if not POLAR_ACCESS_TOKEN:
        raise HTTPException(status_code=500, detail="POLAR_ACCESS_TOKEN no configurado")

    headers = {"Authorization": f"Bearer {POLAR_ACCESS_TOKEN}"}
    url = "https://api.polar.sh/v1/subscriptions/"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error al consultar Polar: {str(e)}")

    subscriptions = response.json().get("items", [])

    synced = 0
    for sub in subscriptions:
        customer_email = sub.get("customer", {}).get("email")
        product_name = sub.get("product", {}).get("name", "")

        if not customer_email:
            continue

        # Mapear nombre de producto a plan
        if "PRO" in product_name:
            new_plan = models.PlanType.PRO
        elif "ENTERPRISE" in product_name:
            new_plan = models.PlanType.ENTERPRISE
        else:
            new_plan = models.PlanType.FREE

        org = crud.get_organization_by_email(db, customer_email)
        if org and org.plan != new_plan:
            org.plan = new_plan
            db.commit()
            synced += 1
            print(f"✅ Plan de {org.name} actualizado a {new_plan.value}")

    return {"status": "success", "synced": synced, "total_checked": len(subscriptions)}