"""Interactive chat with the fully integrated Agentic RAG system."""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(__file__))

from strands import Agent
from strands.models.bedrock import BedrockModel
from strands_tools import retrieve
from tools.graph_tools import search_context_graph, record_decision, ingest_email_decision

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
    tools=[retrieve, search_context_graph, record_decision, ingest_email_decision],
    system_prompt=(
        "You are the AFS Metrics Assistant for AWS CapEx financial operations. "
        "Use retrieve for metric definitions and policies. "
        "Use search_context_graph for decision history and relationships. "
        "Use record_decision when you make classifications or recommendations. "
        "Always explain both WHAT is true and WHY."
    ),
)

print("🤖 AFS Metrics Assistant")
print("=" * 40)
print("I can answer questions using:")
print("  📚 Knowledge Base (metric definitions, recon rules)")
print("  🔗 Context Graph (decision history, system relationships)")
print("  📝 Decision Recording (audit trail)")
print("  📧 Email Decision Capture (extract decisions from emails)")
print()
print("Try asking:")
print('  "What metrics track PO aging for LLE?"')
print('  "Why is the PO aging threshold 90 days?"')
print('  "Classify risk on 47 POs totaling $3.2M"')
print('  Paste an email and ask: "Capture the decision from this email"')
print()
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
