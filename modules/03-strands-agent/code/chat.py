"""Interactive chat with the multi-agent system."""
import os
import json
from strands import Agent, tool
from strands.models.bedrock import BedrockModel
from strands_tools import retrieve

config_path = os.path.join(os.path.dirname(__file__), "..", "..", "kb_config.json")
with open(config_path) as f:
    config = json.load(f)

os.environ["KNOWLEDGE_BASE_ID"] = config["knowledge_base_id"]

model = BedrockModel(
    model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
    region_name="us-east-1",
)

agent = Agent(
    model=model,
    tools=[retrieve],
    system_prompt=(
        "You are the AFS Metrics Assistant. "
        "Search the knowledge base to answer questions about metric definitions, "
        "reconciliation rules, namespace configurations, and compliance policies. "
        "Be concise and cite specific metrics, thresholds, and policy sections."
    ),
)

print("🤖 AFS Metrics Assistant")
print("Ask me about metric definitions, reconciliation rules, or compliance policies.")
print("Type 'quit' to exit.\n")

while True:
    try:
        query = input("You: ").strip()
    except (EOFError, KeyboardInterrupt):
        break

    if not query or query.lower() in ("quit", "exit", "q"):
        print("Goodbye!")
        break

    result = agent(query)
    print(f"\nAssistant: {result}\n")
