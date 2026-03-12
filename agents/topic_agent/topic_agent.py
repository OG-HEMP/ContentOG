import logging

from skills.topic_reasoning.topic_reasoning import generate_topics

logger = logging.getLogger(__name__)


class TopicAgent:
    def run(self, context):
        topics = generate_topics(
            context.get("clustered_titles", {}),
            context.get("paa_questions", []),
            [context.get("keyword", "content strategy")],
            context.get("clustered_articles", {}),
        )
        context["topics"] = topics
        logger.info("Identified %d topics", len(topics))
        return context
