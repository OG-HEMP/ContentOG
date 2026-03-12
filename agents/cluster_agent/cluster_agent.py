from skills.clustering.clustering import detect_clusters

class ClusterAgent:
    def run(self):
        print("Agent: Cluster Agent is running...")
        clusters = detect_clusters([])
        print("Agent: Clusters detected.")
