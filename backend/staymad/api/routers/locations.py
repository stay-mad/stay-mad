"""Geographic reference endpoints.

Authority: docs/contracts/openapi.yaml
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.staymad.api.dependencies import get_db
from backend.staymad.api.schemas import GeoLevel, Location, LocationsResponse
from backend.staymad.db.models.location import Location as LocationModel

router = APIRouter(prefix="/locations", tags=["locations"])


@router.get("", response_model=LocationsResponse)
def list_locations(
    db: Annotated[Session, Depends(get_db)],
    geo_level: GeoLevel | None = None,
    parent_province: str | None = None,
):
    """List locations that have active events, with optional geo_level or province filter."""
    stmt = select(LocationModel).where(LocationModel.events.any())

    if geo_level is not None:
        stmt = stmt.where(
            LocationModel.geo_level.in_([geo_level.value, geo_level.value.upper()])
        )

    if parent_province is not None:
        stmt = stmt.where(LocationModel.province.ilike(f"%{parent_province}%"))

    locations_db = db.scalars(stmt).all()
    results = []
    for loc in locations_db:
        raw_val = (
            loc.geo_level.value
            if hasattr(loc.geo_level, "value")
            else str(loc.geo_level)
        )
        g_lvl = GeoLevel(raw_val.lower())
        results.append(
            Location(
                id=loc.id,
                city=loc.city,
                district=loc.district,
                province=loc.province,
                country=loc.country or "Indonesia",
                geo_level=g_lvl,
                canonical_name=loc.canonical_name,
            )
        )

    return LocationsResponse(locations=results)
