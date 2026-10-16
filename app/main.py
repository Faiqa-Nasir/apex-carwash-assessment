"""The FastAPI app: routers, error handlers and OpenAPI metadata.

Run with: uvicorn app.main:app --reload
"""

from fastapi import FastAPI

from app.api.errors import add_error_handlers
from app.api.routers import appointments, catalog, customers

DESCRIPTION = """
An API for a car wash company with several branches. Each branch takes one
appointment at a time, so two appointments at the same branch can never
overlap.

**Token.** Every endpoint needs a token. Click **Authorize** and enter it.
With Docker the token is `demo-token-change-me`. Without Docker, it is the
`API_TOKEN` in your `.env` file.

**Times.** Send times with a timezone, like `2030-01-10T10:00:00+03:00`.
Times always come back in UTC (ending in `Z`). The `date` filter means that
day in the branch's own time.

**Errors.** Every error looks the same:
`{"error": {"code": "...", "message": "...", "details": [...]}}`.
400 = breaks a rule, 401 = token missing or wrong, 404 = id not found,
409 = clashes with existing data, 422 = badly formed request.

**Try it.** The example requests below use the sample data ids:
branch `...b001` (Riyadh), service `...a002` (Exterior Wash, 30 minutes),
customer `...c001` (Sara).
"""

TAGS = [
    {"name": "catalog", "description": "Branches and services. Read only."},
    {"name": "customers", "description": "Add and see customers."},
    {
        "name": "appointments",
        "description": "Book, list, cancel and complete.",
    },
]

app = FastAPI(
    title="Car Wash Operations API",
    version="0.1.0",
    description=DESCRIPTION,
    openapi_tags=TAGS,
)

app.include_router(catalog.router)
app.include_router(customers.router)
app.include_router(appointments.router)
add_error_handlers(app)
