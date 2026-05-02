"""Evaluate retrieval quality across chunking strategies."""
import os
import sys
import json
import boto3
from rich.console import Console
from rich.table import Table

console = Console()
bedrock_runtime = boto3.client("bedrock-agent-runtime")

config_path = os.path.join(os.path.dirname(__file__), "..", "..", "kb_config.json")
with open(config_path) as f:
    config = json.load(f)

KB_ID = config["knowledge_base_id"]
query = " ".join(sys.argv[1:]) or "What metrics track PO aging for the LLE category?"

console.print(f"\n🔍 [bold]Query:[/] {query}\n")

# Retrieve from the KB (all data sources contribute to the same index)
response = bedrock_runtime.retrieve(
    knowledgeBaseId=KB_ID,
    retrievalQuery={"text": query},
    retrievalConfiguration={
        "vectorSearchConfiguration": {"numberOfResults": 10}
    },
)

results = response["retrievalResults"]

table = Table(title="Retrieval Results")
table.add_column("#", style="cyan", width=3)
table.add_column("Score", justify="right", width=8)
table.add_column("Source", width=30)
table.add_column("Preview", width=60)

for i, result in enumerate(results, 1):
    score = f"{result.get('score', 0):.4f}"
    text = result.get("content", {}).get("text", "")[:100].replace("\n", " ")
    location = result.get("location", {}).get("s3Location", {}).get("uri", "unknown")
    source = location.split("/")[-1] if "/" in location else location
    table.add_row(str(i), score, source, text + "...")

console.print(table)

# Generate answers using retrieve-and-generate
MODEL_ARN = (
    "arn:aws:bedrock:us-east-1::foundation-model/"
    "anthropic.claude-3-5-sonnet-20241022-v2:0"
)

rag_response = bedrock_runtime.retrieve_and_generate(
    input={"text": query},
    retrieveAndGenerateConfiguration={
        "type": "KNOWLEDGE_BASE",
        "knowledgeBaseConfiguration": {
            "knowledgeBaseId": KB_ID,
            "modelArn": MODEL_ARN,
        },
    },
)

console.print(f"\n💬 [bold]Generated Answer:[/]")
console.print(rag_response["output"]["text"])

citations = rag_response.get("citations", [])
if citations:
    console.print(f"\n📚 [bold]Citations:[/]")
    for citation in citations:
        for ref in citation.get("retrievedReferences", []):
            uri = ref.get("location", {}).get("s3Location", {}).get("uri", "")
            console.print(f"  • {uri}")
