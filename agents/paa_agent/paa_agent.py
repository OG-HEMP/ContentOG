import logging

from database.db_client import db_client
from skills.paa_extraction.paa_extraction import extract_paa_questions

logger = logging.getLogger(__name__)


class PaaAgent:
    def run(self, context):
        keyword = context.get("keyword", "content strategy")
        questions = extract_paa_questions(keyword)
        for question in questions:
            db_client.insert_paa_question(keyword, question)
        context["paa_questions"] = questions
        logger.info("PAA extracted %d questions", len(questions))
        return context
