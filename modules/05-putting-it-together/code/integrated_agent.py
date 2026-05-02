"""Integrated Strands agent with KB retrieval + context graph + decision recording."""
import os
import sys
import json

# Add tools directory to path
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

SYSTEM_PROMPT = """You are the AFS Metrics Assistant for AWS CapEx financial operations.

You have access to three capabilities:

1. **retrieve** — Search the knowledge base for metric definitions, reconciliation rules,
   namespace configurations, and compliance policies. Use this for WHAT is true now.

2. **search_context_graph** — Search the context graph for system relationships, decision
   history, and threshold change rationale. Use this for WHY things are the way they are.

3. **record_decision** — After making a recommendation or classification, record your
   reasoning as a decision trace for future audit trail.

4. **ingest_email_decision** — When given an email thread containing a decision about
   thresholds, categories, or configurations, extract the decision and store it in the
   context graph. This captures the event clock from email communications.

## How to Answer Questions

For every question:
1. Search the KB for relevant metric definitions and rules
2. Search the graph for related decisions and system relationships
3. Synthesize both: explain WHAT the current rule is and WHY it was set that way
4. If you make a classification or recommendation, record it as a decision trace

Always cite specific metric names, thresholds, and decision IDs.
Distinguish between current configuration (KB) and historical context (graph)."""

agent = Agent(
    model=model,
    tools=[retrieve, search_context_graph, record_decision, ingest_email_decision],
    system_prompt=SYSTEM_PROMPT,
)

# Demo queries that exercise all three tools
queries = [
    "What metrics track PO aging for the LLE category and why is the threshold set to 90 days?",
    "We have 47 EMEA POs aging >90 days totaling $3.2M. Classify the risk and record your decision.",
    (
        "Please capture the decision from this email:\n\n"
        "From: Sarah Chen (FBI CapEx Lead)\n"
        "Date: 2024-10-15\n"
        "Subject: RE: PO Aging Threshold Review\n\n"
        "After reviewing the Q4 audit findings, I'm approving the change to increase "
        "the PO aging threshold from 60 days to 90 days. The 60-day threshold was "
        "generating approximately 40% false positives during the Q3 close cycle. "
        "The audit team confirmed that 90 days better reflects actual procurement "
        "timelines for infrastructure equipment. Expected to reduce false positive "
        "alerts by ~35%."
    ),
    "Now search the graph — what decisions have been made about PO aging thresholds and who approved them?",
]

for query in queries:
    print(f"\n{'='*70}")
    print(f"🔍 Query: {query}")
    print(f"{'='*70}")
    result = agent(query)
    print(f"\n💬 Answer:\n{result}")
    print()
