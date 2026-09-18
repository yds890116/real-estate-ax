"""data/sample/감정평가서(설정상 APPRAISAL_SAMPLE_DIR) 폴더의 PDF들을 파싱해 appraisal_cases에 적재한다."""

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.appraisal_case import AppraisalCase
from app.services.appraisal_parser import AppraisalParsingError, parse_appraisal_pdf


def ingest_appraisal_samples(db: Session) -> dict:
    sample_dir = settings.APPRAISAL_SAMPLE_DIR
    if not sample_dir.exists():
        return {"files_found": 0, "files_parsed": 0, "files_failed": [], "cases_inserted": 0, "cases_skipped_duplicate": 0}

    pdf_paths = sorted(sample_dir.glob("*.pdf"))
    files_parsed = 0
    files_failed: list[dict] = []
    inserted = 0
    skipped = 0

    for path in pdf_paths:
        try:
            rows = parse_appraisal_pdf(path)
        except AppraisalParsingError as e:
            files_failed.append({"file": path.name, "reason": str(e)})
            continue

        files_parsed += 1
        for row in rows:
            duplicate = (
                db.query(AppraisalCase)
                .filter_by(source_file=path.name, case_type=row.case_type, code=row.code)
                .first()
            )
            if duplicate is not None:
                skipped += 1
                continue

            db.add(
                AppraisalCase(
                    source_file=path.name,
                    case_type=row.case_type,
                    code=row.code,
                    sido=row.sido,
                    sigungu=row.sigungu,
                    dong=row.dong,
                    jibun=row.jibun,
                    complex_name=row.complex_name,
                    dong_ho=row.dong_ho,
                    usage=row.usage,
                    exclusive_area=row.exclusive_area,
                    event_date=row.event_date,
                    purpose=row.purpose,
                    amount=row.amount,
                    unit_price=row.unit_price,
                    location_note=row.location_note,
                    approval_date=row.approval_date,
                )
            )
            inserted += 1

    db.commit()

    return {
        "files_found": len(pdf_paths),
        "files_parsed": files_parsed,
        "files_failed": files_failed,
        "cases_inserted": inserted,
        "cases_skipped_duplicate": skipped,
    }
