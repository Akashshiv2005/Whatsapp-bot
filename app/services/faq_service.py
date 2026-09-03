from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.faq import FAQ
from app.core.logging import logger


class FAQService:
    @staticmethod
    async def match_faq(db: AsyncSession, query_text: str) -> Optional[FAQ]:
        """Match incoming user query against database FAQs using keywords."""
        if not query_text or len(query_text.strip()) < 3:
            return None

        clean_query = query_text.lower().strip()
        query_words = set(clean_query.split())

        result = await db.execute(select(FAQ).where(FAQ.active == True))
        faqs = result.scalars().all()

        best_faq = None
        best_score = 0

        for faq in faqs:
            score = 0
            # Check keywords
            for kw in (faq.keywords or []):
                kw_clean = kw.lower().strip()
                if kw_clean in clean_query:
                    score += 3
                elif any(word in kw_clean for word in query_words):
                    score += 1

            # Check question similarity
            q_words = set(faq.question.lower().split())
            overlap = query_words.intersection(q_words)
            score += len(overlap) * 2

            if score > best_score and score >= 2:
                best_score = score
                best_faq = faq

        if best_faq:
            logger.info(f"Matched FAQ id={best_faq.id} with score={best_score} for query='{query_text}'")
        return best_faq


faq_service = FAQService()
