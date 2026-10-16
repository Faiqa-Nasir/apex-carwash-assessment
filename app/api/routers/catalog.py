"""GET /branches, GET /services. Seeded data, readable without a token."""

from fastapi import APIRouter, Depends, Query

from app.api.errors import error_responses
from app.api.helpers import get_uow
from app.api.schemas import BranchPage, ServicePage
from app.booking.services import queries
from app.booking.services.unit_of_work import UnitOfWork

router = APIRouter(tags=["catalog"])


@router.get("/branches", responses=error_responses(422))
def list_branches(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    uow: UnitOfWork = Depends(get_uow),
) -> BranchPage:
    """All branches, by name. Each has its own IANA timezone."""
    page = queries.list_branches(uow, limit, offset)
    return BranchPage(items=page.items, total=page.total, limit=limit, offset=offset)


@router.get("/services", responses=error_responses(422))
def list_services(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    uow: UnitOfWork = Depends(get_uow),
) -> ServicePage:
    """All services, by name. Every branch offers every service at the same price."""
    page = queries.list_services(uow, limit, offset)
    return ServicePage(items=page.items, total=page.total, limit=limit, offset=offset)
