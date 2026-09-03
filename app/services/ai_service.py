from typing import Optional
from app.core.logging import logger


class AIService:
    """Modular AI Interface for future Natural Language & AI-assisted lead qualification."""

    @staticmethod
    async def process_unknown_message(user_message: str, conversation_context: Optional[dict] = None) -> Optional[str]:
        """Placeholder interface for future LLM integration.
        Returns AI generated answer or None if AI is disabled / fallback to human.
        """
        logger.info(f"AI Service called for unknown message: '{user_message}' (V1 AI Disabled - returning None)")
        return None

    @staticmethod
    async def extract_service_intent(user_message: str) -> Optional[str]:
        """Placeholder for AI intent classification."""
        return None


ai_service = AIService()
