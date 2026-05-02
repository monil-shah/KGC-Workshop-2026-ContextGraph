"""Populate the Neptune Analytics graph with entities and relationships."""
import os
import json
import glob
import boto3

neptune = boto3.client("neptune-graph")
bedrock_runtime = boto3.client("bedrock-runtime")

config_path = os.path.join(os.path.dirname(__file__), "..", "..", "kb_config.json")
with open(config_path) as f:
    config = json.load(f)

GRAPH_ID = config["neptune_graph_id"]
EMBED_MODEL = "amazon.titan-embed-text-v2:0"


def get_embedding(text: str) -> list[float]:
    """Generate embedding using Titan Embeddings V2."""
    response = bedrock_runtime.invoke_model(
        modelId=EMBED_MODEL,
        body=json.dumps({"inputText": text[:8000]}),
    )
    return json.loads(response["body"].read())["embedding"]


def extract_entities_with_llm(text: str, doc_name: str) -> dict:
    """Use Claude to extract entities and relationships from text."""
    prompt = f"""Extract entities and relationships from this AFS financial operations document.

Document: {doc_name}
---
{text[:6000]}
---

Return a JSON object with:
- "entities": list of {{"name": str, "type": str, "description": str}}
  Types: System, Metric, Namespace, Dimension, Policy, Decision, Process
- "relationships": list of {{"source": str, "target": str, "type": str, "description": str}}
  Relationship types: FEEDS_INTO, DEFINES, HAS_DIMENSION, RECONCILES, DECIDED, CAUSED_BY, REPLACES, CONTAINS, TRACKS
- "decisions": list of {{"id": str, "title": str, "date": str, "context": str, "decision": str, "rationale": str}}

Return ONLY valid JSON, no other text."""

    response = bedrock_runtime.invoke_model(
        modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }),
    )
    result = json.loads(response["body"].read())
    content = result["content"][0]["text"]

    # Parse JSON from response
    start = content.find("{")
    end = content.rfind("}") + 1
    return json.loads(content[start:end])


def execute_query(query: str):
    """Execute an openCypher query against Neptune Analytics."""
    try:
        response = neptune.execute_query(
            graphIdentifier=GRAPH_ID,
            queryString=query,
            language="OPEN_CYPHER",
        )
        return response.get("payload")
    except Exception as e:
        print(f"  Query error: {e}")
        return None


# Load documents
data_dir = os.path.join(
    os.path.dirname(__file__), "..", "..", "01-knowledge-base-setup", "data"
)
doc_files = glob.glob(os.path.join(data_dir, "*.md"))

print(f"Processing {len(doc_files)} documents...\n")

all_entities = []
all_relationships = []
all_decisions = []

for filepath in doc_files:
    doc_name = os.path.basename(filepath)
    print(f"📄 Processing: {doc_name}")

    with open(filepath) as f:
        text = f.read()

    # Create document node
    doc_embedding = get_embedding(text[:2000])
    execute_query(f"""
        CREATE (d:Document {{
            name: '{doc_name}',
            content_preview: '{text[:200].replace("'", "")}',
            char_count: {len(text)},
            embedding: {doc_embedding}
        }})
    """)

    # Extract entities and relationships
    extracted = extract_entities_with_llm(text, doc_name)

    # Create entity nodes
    for entity in extracted.get("entities", []):
        name = entity["name"].replace("'", "")
        desc = entity.get("description", "").replace("'", "")
        entity_type = entity["type"]
        embedding = get_embedding(f"{name}: {desc}")

        execute_query(f"""
            MERGE (e:{entity_type} {{name: '{name}'}})
            ON CREATE SET
                e.description = '{desc}',
                e.embedding = {embedding}
        """)

        # Link entity to document
        execute_query(f"""
            MATCH (d:Document {{name: '{doc_name}'}})
            MATCH (e:{entity_type} {{name: '{name}'}})
            MERGE (d)-[:MENTIONS]->(e)
        """)

        all_entities.append(entity)
        print(f"  + Entity: [{entity_type}] {name}")

    # Create relationships
    for rel in extracted.get("relationships", []):
        source = rel["source"].replace("'", "")
        target = rel["target"].replace("'", "")
        rel_type = rel["type"]
        desc = rel.get("description", "").replace("'", "")

        execute_query(f"""
            MATCH (s {{name: '{source}'}})
            MATCH (t {{name: '{target}'}})
            MERGE (s)-[r:{rel_type}]->(t)
            ON CREATE SET r.description = '{desc}'
        """)

        all_relationships.append(rel)
        print(f"  → Relationship: {source} --[{rel_type}]--> {target}")

    # Create decision trace nodes
    for decision in extracted.get("decisions", []):
        dec_id = decision["id"].replace("'", "")
        title = decision["title"].replace("'", "")
        context = decision.get("context", "").replace("'", "")
        dec_text = decision.get("decision", "").replace("'", "")
        rationale = decision.get("rationale", "").replace("'", "")
        date = decision.get("date", "unknown")

        embedding = get_embedding(f"{title}: {context} {dec_text} {rationale}")

        execute_query(f"""
            CREATE (dec:Decision {{
                id: '{dec_id}',
                title: '{title}',
                date: '{date}',
                context: '{context}',
                decision: '{dec_text}',
                rationale: '{rationale}',
                embedding: {embedding}
            }})
        """)

        # Link decision to document
        execute_query(f"""
            MATCH (d:Document {{name: '{doc_name}'}})
            MATCH (dec:Decision {{id: '{dec_id}'}})
            MERGE (d)-[:CONTAINS_DECISION]->(dec)
        """)

        all_decisions.append(decision)
        print(f"  ★ Decision: {title}")

    print()

print(f"✅ Graph populated!")
print(f"   Entities: {len(all_entities)}")
print(f"   Relationships: {len(all_relationships)}")
print(f"   Decisions: {len(all_decisions)}")
