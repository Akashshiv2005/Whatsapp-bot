from fastapi import APIRouter
from app.api.v1.services import router as services_router
from app.api.v1.menu_options import router as menu_options_router
from app.api.v1.leads import router as leads_router
from app.api.v1.conversations import router as conversations_router
from app.api.v1.messages import router as messages_router
from app.api.v1.faqs import router as faqs_router
from app.api.v1.templates import router as templates_router
from app.api.v1.automation import router as automation_router
from app.api.v1.analytics import router as analytics_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(services_router)
api_v1_router.include_router(menu_options_router)
api_v1_router.include_router(leads_router)
api_v1_router.include_router(conversations_router)
api_v1_router.include_router(messages_router)
api_v1_router.include_router(faqs_router)
api_v1_router.include_router(templates_router)
api_v1_router.include_router(automation_router)
api_v1_router.include_router(analytics_router)
