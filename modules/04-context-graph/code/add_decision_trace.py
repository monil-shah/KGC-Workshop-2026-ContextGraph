"""Demonstrate capturing agent decision traces in the context graph."""
import os
import json
from datetime import datetime, timezone
import boto3

neptune = boto3.client("neptune-graph")
bedrock_runtime = boto3.client("bedrock-runtime")

config_path = os.path.join(os.path.dirname(__file__), "..", "..", "kb_config.json")
with open(config_path) as f:
    config = json.load(f)

GRAPH_ID = config["neptune_graph_id"]


def get_embedding(text: str) -> list[float]:
    response = bedrock_runtime.invoke_model(
        modelId="amazon.titan-embed-text-v2:0",
        body=json.dumps({"inputText": text}),
    )
    return json.loads(response["body"].read())["embedding"]


def execute_query(cypher: str):
    try:
        neptune.execute_query(
            graphIdentifier=GRAPH_ID,
            queryString=cypher,
            language="OPEN_CYPHER",
        )
    except Exception as e:
        print(f"  Query error: {e}")


# Simulate an agent interaction and capture the decision trace
print("Simulating agent interaction...\n")

# The scenario: analyst asks about PO risk during month-end close
user_query = "Classify risk on 47 EMEA POs aging >90 days totaling $3.2M"
retrieved_context = [
    "po_aging_not_invoiced: COUNT+SUM, threshold >90 days, dimensions: entity, currency",
    "Escalation: >$500K or >120 days → FBI CapEx lead within 24 hours",
    "GRC-002: All POs invoiced within 90 days or escalated",
]
agent_reasoning = (
    "47 POs totaling $3.2M exceeds $500K HIGH risk threshold. "
    "12 POs >$500K each are HIGH risk. 35 POs <$100K are LOW risk. "
    "GRC-002 requires escalation for POs >90 days."
)
agent_decision = "Classified 12 HIGH risk ($2.4M) and 35 LOW risk ($800K). Escalating HIGH risk to FBI CapEx lead."
timestamp = datetime.now(timezone.utc).isoformat()

print(f"  User Query: {user_query}")
print(f"  Retrieved: {len(retrieved_context)} chunks")
print(f"  Reasoning: {agent_reasoning}")
print(f"  Decision: {agent_decision}")

# Create the decision trace node
trace_id = f"TRACE-{datetime.now().strftime('%Y%m%d%H%M%S')}"
trace_text = f"{user_query} {agent_reasoning} {agent_decision}"
embedding = get_embedding(trace_text)

print(f"\nRecording decision trace: {trace_id}")

execute_query(f"""
    CREATE (t:DecisionTrace {{
        id: '{trace_id}',
        timestamp: '{timestamp}',
        user_query: '{user_query}',
        retrieved_chunks: {len(retrieved_context)},
        reasoning: '{agent_reasoning.replace("'", "")}',
        decision: '{agent_decision.replace("'", "")}',
        confidence: 0.92,
        embedding: {embedding}
    }})
""")

# Link to relevant entities
for entity_name in ["po_aging_not_invoiced", "GRC-002", "EMEA"]:
    execute_query(f"""
        MATCH (t:DecisionTrace {{id: '{trace_id}'}})
        MATCH (e {{name: '{entity_name}'}})
        MERGE (t)-[:CONSIDERED]->(e)
    """)

execute_query(f"""
    MATCH (t:DecisionTrace {{id: '{trace_id}'}})
    MATCH (e {{name: 'po_aging_not_invoiced'}})
    MERGE (t)-[:RECOMMENDED]->(e)
""")

print("\n✅ Decision trace recorded in context graph!")
print("\nThis trace captures:")
print("  • WHAT was asked (user query)")
print("  • WHAT was retrieved (KB chunks)")
print("  • WHY the decision was made (reasoning)")
print("  • WHAT was decided (recommendation)")
print("  • WHEN it happened (timestamp)")
print("  • WHAT was considered (entity links)")
print("\nFuture queries about compute recommendations will find this trace,")
print("giving the agent precedent for similar decisions.")

# Demonstrate querying the trace
print(f"\n{'='*60}")
print("Querying decision traces for 'compute' decisions...")
print(f"{'='*60}")

query_embedding = get_embedding("compute service recommendation")
result = neptune.execute_query(
    graphIdentifier=GRAPH_ID,
    queryString=f"""
        CALL neptune.algo.vectors.topKByNode({{
            queryVector: {query_embedding},
            topK: 3,
            nodeLabels: ['DecisionTrace']
        }})
        YIELD node, score
        RETURN node.id AS id, node.user_query AS query,
               node.decision AS decision, node.reasoning AS reasoning,
               node.timestamp AS timestamp, score
        ORDER BY score DESC
    """,
    language="OPEN_CYPHER",
)

traces = json.loads(result["payload"].read())
for t in traces.get("results", []):
    print(f"\n  [{t.get('score', 0):.3f}] {t.get('id', '')}")
    print(f"  Query: {t.get('query', '')}")
    print(f"  Decision: {t.get('decision', '')}")
    print(f"  When: {t.get('timestamp', '')}")
