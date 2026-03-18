from fastapi import APIRouter, Depends
from sqlmodel import Session, text

from database import get_session

router = APIRouter(prefix="/api/stats", tags=["stats"])

# 單一查詢取得所有統計 (合併 3 個 round-trip 為 1 個)
_STATS_SQL = text("""
WITH
  basic AS (
    SELECT
      COUNT(*) AS total,
      COUNT(*) FILTER (WHERE success = true) AS total_pass,
      COUNT(*) FILTER (WHERE success = false) AS total_fail,
      COUNT(*) FILTER (WHERE success IS NULL) AS total_pending
    FROM test_runs
  ),
  cats AS (
    SELECT category, COUNT(*) AS cnt
    FROM test_runs WHERE category IS NOT NULL
    GROUP BY category
  ),
  sevs AS (
    SELECT severity, COUNT(*) AS cnt
    FROM test_runs WHERE severity IS NOT NULL
    GROUP BY severity
  )
SELECT
  b.total, b.total_pass, b.total_fail, b.total_pending,
  (SELECT COUNT(*) FROM attack_templates) AS total_templates,
  (SELECT json_agg(json_build_object('k', c.category, 'v', c.cnt)) FROM cats c) AS cat_json,
  (SELECT json_agg(json_build_object('k', s.severity, 'v', s.cnt)) FROM sevs s) AS sev_json
FROM basic b
""")


@router.get("")
def get_stats(session: Session = Depends(get_session)):
    row = session.exec(_STATS_SQL).one()
    total, total_pass, total_fail, total_pending, total_templates, cat_json, sev_json = row

    category_distribution = {r["k"]: r["v"] for r in (cat_json or [])}
    severity_distribution = {r["k"]: r["v"] for r in (sev_json or [])}

    judged = total_pass + total_fail
    success_rate = (total_pass / judged * 100) if judged > 0 else 0.0

    return {
        "success": True,
        "data": {
            "total_tests": total,
            "total_pass": total_pass,
            "total_fail": total_fail,
            "total_pending": total_pending,
            "success_rate": success_rate,
            "category_distribution": category_distribution,
            "severity_distribution": severity_distribution,
            "total_templates": total_templates,
        },
    }
