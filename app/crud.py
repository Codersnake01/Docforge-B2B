from sqlalchemy.orm import Session
from datetime import datetime, UTC
from app import models, schemas
from app.auth import hash_api_key, generate_api_key_raw, verify_api_key

# ---------- Organization ----------
def get_organization_by_id(db: Session, org_id: int):
    return db.query(models.Organization).filter(models.Organization.id == org_id).first()

def get_organization_by_email(db: Session, email: str):
    return db.query(models.Organization).filter(models.Organization.email == email).first()

def create_organization(db: Session, org_data: schemas.OrganizationCreate):
    db_org = models.Organization(**org_data.model_dump())  # ← corregido: model_dump()
    db.add(db_org)
    db.commit()
    db.refresh(db_org)
    return db_org

# ---------- API Keys ----------
def create_api_key(db: Session, org_id: int, name: str | None = None):
    raw_key = generate_api_key_raw()
    hashed = hash_api_key(raw_key)
    prefix = raw_key[:8]

    db_key = models.APIKey(
        key_prefix=prefix,
        hashed_key=hashed,
        name=name,
        organization_id=org_id
    )
    db.add(db_key)
    db.commit()
    db.refresh(db_key)
    return db_key, raw_key

def get_organization_by_api_key(db: Session, plain_key: str) -> models.Organization | None:
    """Dada una clave sin hashear, busca la organización propietaria."""
    all_keys = db.query(models.APIKey).filter(models.APIKey.is_active == True).all()
    for key in all_keys:
        if verify_api_key(plain_key, key.hashed_key):
            return key.organization
    return None

# ---------- Templates ----------
def create_template(db: Session, org_id: int, template_data: schemas.TemplateCreate):
    db_template = models.Template(
        name=template_data.name,
        description=template_data.description,
        html_content=template_data.html_content,
        placeholders=template_data.placeholders,
        organization_id=org_id
    )
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template

def get_template_by_id_and_org(db: Session, template_id: int, org_id: int):
    return db.query(models.Template).filter(
        models.Template.id == template_id,
        models.Template.organization_id == org_id
    ).first()

def get_templates_by_org(db: Session, org_id: int):
    return db.query(models.Template).filter(models.Template.organization_id == org_id).all()

# ---------- Document & Usage (con límite de plan) ----------
def check_and_increment_usage(db: Session, org: models.Organization) -> bool:
    """Verifica si la organización está bajo el límite mensual según su plan.
       Si está bien, incrementa el contador y devuelve True. Si excede, False."""
    now = datetime.now(UTC)  # ← corregido: datetime.now(UTC)
    year, month = now.year, now.month

    usage_record = db.query(models.Usage).filter(
        models.Usage.organization_id == org.id,
        models.Usage.year == year,
        models.Usage.month == month
    ).first()

    if not usage_record:
        usage_record = models.Usage(
            organization_id=org.id,
            year=year,
            month=month,
            documents_count=0
        )
        db.add(usage_record)
        db.commit()
        db.refresh(usage_record)

    limits = {
        models.PlanType.FREE: 50,
        models.PlanType.PRO: 999999,
        models.PlanType.ENTERPRISE: 999999
    }
    limit = limits.get(org.plan, 50)

    if usage_record.documents_count >= limit:
        return False

    usage_record.documents_count += 1
    db.commit()
    return True

def create_document(db: Session, org_id: int, template_id: int, data_json: str | None = None):
    doc = models.Document(
        template_id=template_id,
        organization_id=org_id,
        data_json=data_json,
        created_at=datetime.now(UTC)  # ← corregido
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc