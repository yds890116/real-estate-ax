from fastapi import APIRouter

from app.api.v1.endpoints import (
    appraisal,
    batch,
    collateral_score,
    court_auction_monitor,
    dashboard,
    hogangnono,
    kb_stats,
    listings,
    market_data,
    onbid_monitor,
    onbid_stats,
    properties,
    registry,
    risk,
    rone_index,
    rtech,
    search,
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
api_router.include_router(onbid_monitor.router, prefix="/onbid-monitor", tags=["onbid-monitor"])
api_router.include_router(court_auction_monitor.router, prefix="/court-auction-monitor", tags=["court-auction-monitor"])
api_router.include_router(rone_index.router, prefix="/rone-index", tags=["rone-index"])
api_router.include_router(kb_stats.router, prefix="/kb-stats", tags=["kb-stats"])
api_router.include_router(rtech.router, prefix="/rtech", tags=["rtech"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(hogangnono.router, prefix="/hogangnono", tags=["hogangnono"])
api_router.include_router(collateral_score.router, prefix="/collateral-score", tags=["collateral-score"])
