from skills.strategy_generation.strategy_generation import generate_strategy

class StrategyAgent:
    def run(self):
        print("Agent: Strategy Agent is running...")
        strategy = generate_strategy([])
        print("Agent: Strategy roadmap generated.")
