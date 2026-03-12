from skills.topic_reasoning.topic_reasoning import reason_topics

class TopicAgent:
    def run(self):
        print("Agent: Topic Agent is running...")
        topic = reason_topics({})
        print("Agent: Topics identified.")
