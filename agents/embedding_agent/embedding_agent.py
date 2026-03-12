from skills.embeddings.embeddings import generate_embeddings

class EmbeddingAgent:
    def run(self):
        print("Agent: Embedding Agent is running...")
        embeddings = generate_embeddings("placeholder text")
        print("Agent: Embeddings generated.")
