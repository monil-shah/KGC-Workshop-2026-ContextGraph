"""A simple Strands agent with Knowledge Base retrieval."""
import os
import json
from strands import Agent
from strands.models.bedrock import BedrockModel
from strands_tools import retrieve

# Load KB config
config_path = os.path.join(os.path.dirname(__file__), "..", "..", "kb_config.json")
with open(config_path) as f:
    config = json.load(f)

# Set the KB ID for the retrieve tool
os.environ["KNOWLEDGE_BASE_ID"] = config["knowledge_base_id"]

# Create the agent
model = BedrockModel(
    model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
    region_name="us-east-1",
)

agent = Agent(
    model=model,
    tools=[retrieve],
    system_prompt=(
        "You are the AFS Metrics Assistant. "
        "Use the retrieve tool to search the knowledge base for "
        "metric definitions, reconciliation rules, and compliance policies. "
        "Always cite specific metrics, thresholds, and policy sections."
    ),
)

# Test queries
queries = [
    "What metrics track PO aging for the LLE category?",
    "What are the reconciliation rules between AFS and OFA?",
    "What is the escalation process for reconciliation variances over $1M?",
]

for query in queries:
    print(f"\n{'='*60}")
    print(f"🔍 Query: {query}")
    print(f"{'='*60}")
    result = agent(query)
    print(f"\n💬 Answer:\n{result}")
