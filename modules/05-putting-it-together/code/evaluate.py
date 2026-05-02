"""Evaluate KB-only vs Graph-enhanced answers."""
import os
import sys
import json
import boto3
from rich.console import Console
from rich.table import Table

sys.path.insert(0, os.path.dirname(__file__))

console = Console()
bedrock_runtime = boto3.client("bedrock-agent-runtime")
bedrock_rt = boto3.client("bedrock-runtime")

config_path = os.path.join(os.path.dirname(__file__), "..", "..", "kb_config.json")
with open(config_path) as f:
    config = json.load(f)

KB_ID = config["knowledge_base_id"]
MODEL_ARN = (
    "arn:aws:bedrock:us-east-1::foundation-model/"
    "anthropic.claude-3-5-sonnet-20241022-v2:0"
)

# Test queries designed to show the difference
test_queries = [
    {
        "query": "Why is the PO aging threshold set to 90 days?",
        "expected": "Should explain Q4-2024 audit decision, not just state the threshold",
    },
    {
        "query": "What led to adding GENERATOR to the LLE categories?",
        "expected": "Should reference DEC-004 and FY2024 GAAP update",
    },
    {
        "query": "How do AFS and OFA reconcile asset values?",
        "expected": "Should explain matching rules and the decision to use DataStudio Redshift",
    },
]

console.print("\n[bold]📊 Evaluation: KB-Only vs Graph-Enhanced[/]\n")

for test in test_queries:
    query = test["query"]
    console.print(f"[bold cyan]Query:[/] {query}")
    console.print(f"[dim]Expected: {test['expected']}[/]\n")

    # KB-only answer
    kb_response = bedrock_runtime.retrieve_and_generate(
        input={"text": query},
        retrieveAndGenerateConfiguration={
            "type": "KNOWLEDGE_BASE",
            "knowledgeBaseConfiguration": {
                "knowledgeBaseId": KB_ID,
                "modelArn": MODEL_ARN,
            },
        },
    )
    kb_answer = kb_response["output"]["text"]

    # Graph-enhanced answer (using the integrated agent)
    from strands import Agent
    from strands.models.bedrock import BedrockModel
    from strands_tools import retrieve
    from tools.graph_tools import search_context_graph

    os.environ["KNOWLEDGE_BASE_ID"] = KB_ID
    model = BedrockModel(
        model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
        region_name="us-east-1",
    )
    agent = Agent(
        model=model,
        tools=[retrieve, search_context_graph],
        system_prompt=(
            "Answer the question using both the knowledge base (current facts) "
            "and the context graph (decision history and relationships). "
            "Explain both WHAT is true and WHY."
        ),
    )
    graph_answer = str(agent(query))

    # Display comparison
    table = Table(show_header=True, header_style="bold")
    table.add_column("KB-Only Answer", width=40)
    table.add_column("Graph-Enhanced Answer", width=40)
    table.add_row(kb_answer[:300] + "...", graph_answer[:300] + "...")
    console.print(table)
    console.print()

console.print("[bold green]✅ Evaluation complete![/]")
console.print(
    "Notice how graph-enhanced answers include decision context, "
    "rationale, and relationships that KB-only answers miss."
)
