from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.database import Base, engine
from app.routers import leads

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Sales Lead CRM API",
    description="A robust RESTful API for managing sales leads in a state-machine pipeline.",
    version="1.0.0",
)

# Exception handler to return a cleaner validation error response
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "details": exc.errors()
        }
    )

# Register routers
app.include_router(leads.router)


@app.get("/")
def read_root():
    return {
        "message": "Welcome to the Sales Lead CRM API",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "status": "healthy"
    }
