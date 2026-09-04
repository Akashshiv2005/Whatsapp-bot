import sys
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.logging import setup_logging, logger
from app.core.database import engine
from app.api.webhook import router as webhook_router
from app.api.v1.router import api_v1_router
from app.api.simulator import router as simulator_router

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup structured logging
    setup_logging()
    logger.info(f"Starting {settings.APP_NAME} in [{settings.APP_ENV}] mode...")

    # Test database connectivity
    try:
        async with engine.connect() as conn:
            logger.info("Database connection established successfully.")
            
            # Reseed the menus automatically on startup to ensure production DB has the 10-row fix
            try:
                import sys
                from pathlib import Path
                # add root to sys path if not there
                root_dir = str(Path(__file__).parent.parent)
                if root_dir not in sys.path:
                    sys.path.insert(0, root_dir)
                
                from reseed import seed_menus
                logger.info("Running automatic menu reseeding to fix 10-row limit...")
                await seed_menus()
            except Exception as seed_err:
                logger.error(f"Failed to reseed menus: {seed_err}", exc_info=True)

    except Exception as e:
        logger.error(f"Failed to connect to database on startup: {e}", exc_info=True)

    yield

    # Clean shutdown
    logger.info("Disposing database connections...")
    await engine.dispose()
    logger.info("Application shutdown complete.")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Production-ready state-machine WhatsApp Business automation platform for iZone Technologies",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "message": "Something went wrong while processing your request. Please try again or contact support.",
        }
    )


from fastapi.responses import JSONResponse, RedirectResponse

# Root route
@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")

# Health Check
@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "version": "1.0.2-erptour"
    }


# Include Routers
app.include_router(webhook_router)
app.include_router(api_v1_router)
app.include_router(simulator_router)

