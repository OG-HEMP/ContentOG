import logging

from skills.strategy_generation.strategy_generation import generate_strategy

logger = logging.getLogger(__name__)


class StrategyAgent:
    def run(self, context):
        strategy = generate_strategy(
            context.get("topics", []),
            context.get("clustered_articles", {}),
            context.get("paa_questions", []),
            target_domain=context.get("target_domain"),
        )
        context["strategy"] = strategy
        logger.info("Generated strategy artifacts for %d topics", len(context.get("topics", [])))
        return context
