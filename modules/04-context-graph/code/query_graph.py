"""Query the context graph with hybrid vector + graph retrieval."""
import os
import sys
import json
import boto3
from rich.console import Console
from rich.panel import Panel

console = Console()
neptune = boto3.client("neptune-graph")
bedrock_runtime = boto3.client("bedrock-runtime")

config_path = os.path.join(os.path.dirname(__file__), "..", "..", "kb_config.json")
with open(config_path) as f:
    config = json.load(f)

GRAPH_ID = config["neptune_graph_id"]

query = " ".join(sys.argv[1:]) or "Why was the PO aging threshold changed from 60 to 90 days?"
console.print(f"\n🔍 [bold]Query:[/] {query}\n")


def get_embedding(text: str) -> list[float]:
    response = bedrock_runtime.invoke_model(
        modelId="amazon.titan-embed-text-v2:0",
        body=json.dumps({"inputText": text}),
    )
    return json.loads(response["body"].read())["embedding"]


def execute_query(cypher: str):
    try:
        response = neptune.execute_query(
            graphIdentifier=GRAPH_ID,
            queryString=cypher,
            language="OPEN_CYPHER",
        )
        return json.loads(response["payload"].read())
    except Exception as e:
        console.print(f"[red]Query error: {e}[/]")
        return {"results": []}


# Step 1: Vector search — find semantically similar nodes
query_embedding = get_embedding(query)

console.print("[bold cyan]1. Vector Search Results[/]")
vector_results = execute_query(f"""
    CALL neptune.algo.vectors.topKByNode({{
        queryVector: {query_embedding},
        topK: 5
    }})
    YIELD node, score
    RETURN labels(node) AS type, node.name AS name,
           node.description AS description, score
    ORDER BY score DESC
""")

for r in vector_results.get("results", []):
    console.print(
        f"  [{r.get('score', 0):.3f}] "
        f"({', '.join(r.get('type', []))}) "
        f"{r.get('name', 'N/A')}: {r.get('description', '')[:100]}"
    )

# Step 2: Graph traversal — follow relationships from top results
console.print(f"\n[bold cyan]2. Graph Traversal (relationships)[/]")
if vector_results.get("results"):
    top_entity = vector_results["results"][0].get("name", "")
    graph_results = execute_query(f"""
        MATCH (n {{name: '{top_entity}'}})-[r]-(connected)
        RETURN n.name AS source, type(r) AS relationship,
               labels(connected) AS target_type, connected.name AS target,
               connected.description AS target_description
        LIMIT 10
    """)

    for r in graph_results.get("results", []):
        console.print(
            f"  {r.get('source', '')} --[{r.get('relationship', '')}]--> "
            f"({', '.join(r.get('target_type', []))}) {r.get('target', '')}"
        )

# Step 3: Find related decisions
console.print(f"\n[bold cyan]3. Related Decisions (Event Clock)[/]")
decision_results = execute_query(f"""
    CALL neptune.algo.vectors.topKByNode({{
        queryVector: {query_embedding},
        topK: 3,
        nodeLabels: ['Decision']
    }})
    YIELD node, score
    RETURN node.id AS id, node.title AS title, node.date AS date,
           node.context AS context, node.decision AS decision,
           node.rationale AS rationale, score
    ORDER BY score DESC
""")

for r in decision_results.get("results", []):
    console.print(Panel(
        f"[bold]{r.get('title', 'N/A')}[/] ({r.get('date', 'N/A')})\n\n"
        f"[dim]Context:[/] {r.get('context', 'N/A')}\n"
        f"[dim]Decision:[/] {r.get('decision', 'N/A')}\n"
        f"[dim]Rationale:[/] {r.get('rationale', 'N/A')}",
        title=f"Decision {r.get('id', '')} (score: {r.get('score', 0):.3f})",
        border_style="green",
    ))

# Step 4: Compare with vector-only RAG
console.print(f"\n[bold cyan]4. Comparison: Vector-Only vs Graph-Enhanced[/]")
console.print(Panel(
    "Vector-only RAG returns WHAT is true:\n"
    "  → The policy text, the current rule\n\n"
    "Graph-enhanced RAG also returns WHY:\n"
    "  → The decision that created the rule\n"
    "  → The context that motivated it\n"
    "  → Related entities and their connections\n\n"
    "This is the two clock problem solved.",
    title="State Clock vs Event Clock",
    border_style="yellow",
))
