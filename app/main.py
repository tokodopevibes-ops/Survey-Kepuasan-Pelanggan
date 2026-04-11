"""
Kuesioner - Customer Satisfaction Survey System
Main FastAPI application entry point
"""
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager

from app.config import get_settings
from app.database import engine, Base
from app.routers import customer, admin, auth

settings = get_settings()

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler for startup and shutdown events.
    Creates database tables on startup.
    """
    # Startup
    print("Starting Kuesioner application...")
    print(f"Debug mode: {settings.debug}")
    print(f"Database: {settings.db_host}:{settings.db_port}/{settings.db_name}")
    yield
    # Shutdown
    print("Shutting down Kuesioner application...")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Customer Satisfaction Survey System",
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Add rate limit exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="app/templates")


# Include routers
app.include_router(customer.router, tags=["customer"])
app.include_router(admin.router, tags=["admin"])
app.include_router(auth.router, tags=["auth"])


# ============ Root & Health Endpoints ============
@app.get("/", response_class=HTMLResponse)
async def root():
    """
    Root endpoint - redirects to survey list.
    """
    # Note: The customer router handles the actual survey list page
    # This is just a convenience redirect
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/survey")


@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring.
    """
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "version": settings.app_version
    }


# ============ Admin Page Routes (for serving HTML templates) ============
@app.get("/admin/login.html", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    """Serve admin login page."""
    return templates.TemplateResponse("admin/login.html", {"request": request})


@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page_redirect(request: Request):
    """Serve admin login page (without .html)."""
    return templates.TemplateResponse("admin/login.html", {"request": request})


@app.get("/admin/dashboard.html", response_class=HTMLResponse)
async def admin_dashboard_page(request: Request):
    """Serve admin dashboard page."""
    return templates.TemplateResponse("admin/dashboard.html", {"request": request})


@app.get("/admin/questionnaires.html", response_class=HTMLResponse)
async def admin_questionnaires_page(request: Request):
    """Serve admin questionnaires management page."""
    return templates.TemplateResponse("admin/questionnaires.html", {"request": request})


@app.get("/admin/results.html", response_class=HTMLResponse)
async def admin_results_page(request: Request):
    """Serve admin results page."""
    return templates.TemplateResponse("admin/results.html", {"request": request})


# ============ Customer Page Routes ============
@app.get("/survey", response_class=HTMLResponse)
async def survey_list_page(request: Request):
    """
    Serve survey list page (alias for root customer page).
    The actual data is loaded via API by the page itself.
    """
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/")


# ============ Error Handlers ============
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Custom 404 error handler."""
    return templates.TemplateResponse(
        "errors/404.html",
        {"request": request},
        status_code=404
    )


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    """Custom 500 error handler."""
    return templates.TemplateResponse(
        "errors/500.html",
        {"request": request},
        status_code=500
    )


# ============ Startup Event ============
@app.on_event("startup")
async def startup_event():
    """
    Startup event - create database tables if they don't exist.
    Note: In production, use Alembic migrations instead.
    """
    # Only create tables in debug mode
    if settings.debug:
        try:
            Base.metadata.create_all(bind=engine)
            print("Database tables created/verified")
        except Exception as e:
            print(f"Warning: Could not create database tables: {e}")
            print("Please ensure MySQL is running and credentials are correct")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
