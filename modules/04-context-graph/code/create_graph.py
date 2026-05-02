"""Create a Neptune Analytics graph with vector search enabled."""
import os
import json
import time
import boto3

neptune = boto3.client("neptune-graph")

GRAPH_NAME = "workshop-context-graph"

print("Creating Neptune Analytics graph...")
response = neptune.create_graph(
    graphName=GRAPH_NAME,
    provisionedMemory=32,  # 32 GB — minimum for vector search
    vectorSearchConfiguration={"dimension": 1024},  # Titan Embeddings V2 dimension
    publicConnectivity=False,
    replicaCount=0,
    deletionProtection=False,
    tags=[
        {"key": "Project", "value": "agentic-rag-workshop"},
        {"key": "Module", "value": "context-graph"},
    ],
)

graph_id = response["id"]
print(f"Graph created: {graph_id}")
print("Waiting for graph to become available (this takes 5-10 minutes)...")

while True:
    status = neptune.get_graph(graphIdentifier=graph_id)
    state = status["status"]
    print(f"  Status: {state}")
    if state == "AVAILABLE":
        break
    if state in ("FAILED", "DELETING"):
        print(f"❌ Graph creation failed: {state}")
        exit(1)
    time.sleep(30)

endpoint = status["endpoint"]
print(f"\n✅ Graph ready!")
print(f"   Graph ID: {graph_id}")
print(f"   Endpoint: {endpoint}")

# Save config
config_path = os.path.join(os.path.dirname(__file__), "..", "..", "kb_config.json")
with open(config_path) as f:
    config = json.load(f)

config["neptune_graph_id"] = graph_id
config["neptune_endpoint"] = endpoint

with open(config_path, "w") as f:
    json.dump(config, f, indent=2)

print("Saved Neptune config to kb_config.json")
