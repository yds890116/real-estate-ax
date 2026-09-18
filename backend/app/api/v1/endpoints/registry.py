from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.property import Property
from app.models.registry_analysis import RegistryAnalysis
from app.schemas.property import PropertyBase
from app.schemas.registry import RegistryAnalysisResult
from app.services.registry_extract import RegistryExtractionError, extract_text
from app.services.registry_parser import compute_mortgage_total, detect_risk_flags, parse_rights
from app.services.registry_summary import generate_summary
from app.services.valuation_engine import valuation_engine

router = APIRouter()

MAX_FILE_SIZE = 15 * 1024 * 1024  # 15MB


@router.post("/analyze", response_model=RegistryAnalysisResult)
async def analyze_registry(
    file: UploadFile = File(...),
    property_id: int | None = Form(None),
    db: Session = Depends(get_db),
):
    """등기부등본 파일(PDF/PNG/JPG)을 업로드받아 권리관계를 파싱하고 AI 요약을 생성한다."""

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="파일 용량이 너무 큽니다 (최대 15MB).")
    if not content:
        raise HTTPException(status_code=400, detail="빈 파일입니다.")

    db_property: Property | None = None
    if property_id is not None:
        db_property = db.get(Property, property_id)
        if db_property is None:
            raise HTTPException(status_code=404, detail="Property not found")

    try:
        text, file_type = extract_text(file.filename or "unknown", content)
    except RegistryExtractionError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    rights = parse_rights(text)

    estimated_price = None
    property_context = None
    if db_property is not None:
        prop = PropertyBase.model_validate(db_property)
        valuation = valuation_engine.estimate(prop, db)
        estimated_price = valuation.estimated_price
        property_context = f"{db_property.address}, 전용면적 {db_property.exclusive_area}㎡, AI 추정시세 {estimated_price:,}만원"

    risk_flags = detect_risk_flags(rights, estimated_price)
    summary, generation_method = generate_summary(rights, risk_flags, property_context)

    db_analysis = RegistryAnalysis(
        property_id=property_id,
        filename=file.filename or "unknown",
        file_type=file_type,
        raw_text=text,
        rights=[r.model_dump() for r in rights],
        risk_flags=risk_flags,
        summary=summary,
        generation_method=generation_method,
    )
    db.add(db_analysis)
    db.commit()
    db.refresh(db_analysis)

    return RegistryAnalysisResult(
        id=db_analysis.id,
        property_id=db_analysis.property_id,
        filename=db_analysis.filename,
        rights=rights,
        risk_flags=risk_flags,
        summary=summary,
        generation_method=generation_method,
        mortgage_total=compute_mortgage_total(rights) or None,
        estimated_price=estimated_price,
    )
