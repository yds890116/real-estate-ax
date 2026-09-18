from fastapi import APIRouter

from app.api.v1.endpoints import (
    appraisal,
    batch,
    dashboard,
    listings,
    market_data,
    onbid_stats,
    properties,
    registry,
    risk,
    rone_index,
    rtech,
    valuation,
)

api_router = APIRouter()

api_router.include_router(properties.router, prefix="/properties", tags=["properties"])
api_router.include_router(valuation.router, prefix="/valuation", tags=["valuation"])
api_router.include_router(risk.router, prefix="/risk", tags=["risk"])
api_router.include_router(market_data.router, prefix="/market-data", tags=["market-data"])
api_router.include_router(registry.router, prefix="/registry", tags=["registry"])
api_router.include_router(appraisal.router, prefix="/appraisal", tags=["appraisal"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(listings.router, prefix="/listings", tags=["listings"])
api_router.include_router(batch.router, prefix="/batch", tags=["batch"])
api_router.include_router(onbid_stats.router, prefix="/onbid-stats", tags=["onbid-stats"])
api_router.include_router(rone_index.router, prefix="/rone-index", tags=["rone-index"])
api_router.include_router(rtech.router, prefix="/rtech", tags=["rtech"])
