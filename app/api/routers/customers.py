"""POST /customers, GET /customers, GET /customers/{customer_id}.

All need the token: creating is a write, and reads return personal data
(emails and phone numbers).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.errors import error_responses
from app.api.helpers import get_uow, require_token
from app.api.schemas import CustomerIn, CustomerOut, CustomerPage
from app.booking.services import commands, queries
from app.booking.services.unit_of_work import UnitOfWork

router = APIRouter(tags=["customers"], dependencies=[Depends(require_token)])


@router.post("/customers", status_code=201, responses=error_responses(400, 401, 409, 422))
def create_customer(body: CustomerIn, uow: UnitOfWork = Depends(get_uow)) -> CustomerOut:
    """Create a customer. The email is stored lowercase; 409 if it is already used."""
    customer = commands.create_customer(uow, body.name, body.email, body.phone)
    return CustomerOut.model_validate(customer)


@router.get("/customers", responses=error_responses(401, 422))
def list_customers(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    uow: UnitOfWork = Depends(get_uow),
) -> CustomerPage:
    """All customers, oldest first."""
    page = queries.list_customers(uow, limit, offset)
    return CustomerPage(items=page.items, total=page.total, limit=limit, offset=offset)


@router.get("/customers/{customer_id}", responses=error_responses(401, 404, 422))
def get_customer(customer_id: UUID, uow: UnitOfWork = Depends(get_uow)) -> CustomerOut:
    """One customer by id."""
    return CustomerOut.model_validate(queries.get_customer(uow, customer_id))
