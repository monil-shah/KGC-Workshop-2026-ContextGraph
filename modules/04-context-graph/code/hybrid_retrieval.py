"""Hybrid retrieval combining vector search (KB) + graph traversal (Neptune)."""
import os
import sys
import json
import boto3
from rich.console import Console
from rich.table import Table

console = Console()
bedrock_runtime = boto3.client("bedrock-agent-runtime")
bedrock_rt = boto3.client("bedrock-runtime")
neptune = boto3.client("neptune-graph")

config_path = os.path.join(os.path.dirname(__file__), "..", "..", "kb_config.json")
with open(config_path) as f:
    config = json.load(f)

KB_ID = config["knowledge_base_id"]
GRAPH_ID = config["neptune_graph_id"]

query = " ".join(sys.argv[1:]) or "What metrics should I check for month-end close and why were the thresholds set this way?"
console.print(f"\n🔍 [bold]Query:[/] {query}\n")


def get_embedding(text: str) -> list[float]:
    response = bedrock_rt.invoke_model(
        modelId="amazon.titan-embed-text-v2:0",
        body=json.dumps({"inputText": text}),
    )
    return json.loads(response["body"].read())["embedding"]


# --- Source 1: Vector search from Bedrock KB ---
console.print("[bold cyan]Source 1: Bedrock Knowledge Base (Vector Search)[/]")
kb_results = bedrock_runtime.retrieve(
    knowledgeBaseId=KB_ID,
    retrievalQuery={"text": query},
    retrievalConfiguration={"vectorSearchConfiguration": {"numberOfResults": 5}},
)

vector_chunks = []
for r in kb_results["retrievalResults"]:
    text = r.get("content", {}).get("text", "")
    score = r.get("score", 0)
    vector_chunks.append({"text": text, "score": score, "source": "KB"})
    console.print(f"  [{score:.3f}] {text[:100]}...")

# --- Source 2: Graph search from Neptune Analytics ---
console.print(f"\n[bold cyan]Source 2: Neptune Analytics (Graph + Vector)[/]")
query_embedding = get_embedding(query)

# Vector search in graph
graph_response = neptune.execute_query(
    graphIdentifier=GRAPH_ID,
    queryString=f"""
        CALL neptune.algo.vectors.topKByNode({{
            queryVector: {query_embedding},
            topK: 5
        }})
        YIELD node, score
        OPTIONAL MATCH (node)-[r]-(connected)
        RETURN labels(node) AS type, node.name AS name,
               node.description AS description, score,
               collect(DISTINCT {{
                   rel: type(r),
                   target: connected.name,
                   target_type: labels(connected)
               }})[..5] AS connections
        ORDER BY score DESC
    """,
    language="OPEN_CYPHER",
)

graph_data = json.loads(graph_response["payload"].read())
graph_chunks = []
for r in graph_data.get("results", []):
    name = r.get("name", "")
    desc = r.get("description", "")
    score = r.get("score", 0)
    connections = r.get("connections", [])

    context_parts = [f"{name}: {desc}"]
    for conn in connections:
        if conn.get("target"):
            context_parts.append(
                f"  → {conn['rel']}: {conn['target']}"
            )

    full_text = "\n".join(context_parts)
    graph_chunks.append({"text": full_text, "score": score, "source": "Graph"})
    console.print(f"  [{score:.3f}] {name}: {desc[:80]}...")
    for conn in connections[:3]:
        if conn.get("target"):
            console.print(f"    → {conn['rel']}: {conn['target']}")

# --- Source 3: Decision traces ---
console.print(f"\n[bold cyan]Source 3: Decision Traces (Event Clock)[/]")
trace_response = neptune.execute_query(
    graphIdentifier=GRAPH_ID,
    queryString=f"""
        CALL neptune.algo.vectors.topKByNode({{
            queryVector: {query_embedding},
            topK: 3,
            nodeLabels: ['Decision', 'DecisionTrace']
        }})
        YIELD node, score
        RETURN labels(node) AS type, node.title AS title,
               node.decision AS decision, node.rationale AS rationale,
               node.context AS context, score
        ORDER BY score DESC
    """,
    language="OPEN_CYPHER",
)

trace_data = json.loads(trace_response["payload"].read())
for r in trace_data.get("results", []):
    title = r.get("title", r.get("decision", "N/A"))
    rationale = r.get("rationale", r.get("context", ""))
    score = r.get("score", 0)
    graph_chunks.append({
        "text": f"Decision: {title}. Rationale: {rationale}",
        "score": score,
        "source": "Decision",
    })
    console.print(f"  [{score:.3f}] {title}: {rationale[:80]}...")

# --- Reciprocal Rank Fusion ---
console.print(f"\n[bold cyan]Fused Results (Reciprocal Rank Fusion)[/]")

K = 60  # RRF constant
all_items = {}

for rank, chunk in enumerate(sorted(vector_chunks, key=lambda x: -x["score"])):
    key = chunk["text"][:100]
    all_items.setdefault(key, {"text": chunk["text"], "rrf_score": 0, "sources": []})
    all_items[key]["rrf_score"] += 1 / (K + rank + 1)
    all_items[key]["sources"].append(chunk["source"])

for rank, chunk in enumerate(sorted(graph_chunks, key=lambda x: -x["score"])):
    key = chunk["text"][:100]
    all_items.setdefault(key, {"text": chunk["text"], "rrf_score": 0, "sources": []})
    all_items[key]["rrf_score"] += 1 / (K + rank + 1)
    all_items[key]["sources"].append(chunk["source"])

fused = sorted(all_items.values(), key=lambda x: -x["rrf_score"])[:5]

table = Table(title="Top 5 Fused Results")
table.add_column("RRF Score", justify="right", width=10)
table.add_column("Sources", width=15)
table.add_column("Content", width=60)

for item in fused:
    table.add_row(
        f"{item['rrf_score']:.4f}",
        ", ".join(set(item["sources"])),
        item["text"][:120] + "...",
    )

console.print(table)

# --- Generate final answer with all context ---
console.print(f"\n[bold cyan]Final Answer (with full context)[/]")
context = "\n\n".join(item["text"][:500] for item in fused)

response = bedrock_rt.invoke_model(
    modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
    body=json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": (
            f"Answer this question using the provided context. "
            f"Include both WHAT is true and WHY (cite decisions and rationale).\n\n"
            f"Question: {query}\n\nContext:\n{context}"
        )}],
    }),
)

answer = json.loads(response["body"].read())["content"][0]["text"]
console.print(f"\n💬 {answer}")
