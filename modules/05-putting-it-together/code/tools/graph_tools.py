"""Custom Strands tools for Neptune Analytics context graph."""
import os
import json
from datetime import datetime, timezone
from strands import tool
import boto3

neptune = boto3.client("neptune-graph")
bedrock_rt = boto3.client("bedrock-runtime")

config_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "kb_config.json")
with open(config_path) as f:
    _config = json.load(f)

GRAPH_ID = _config["neptune_graph_id"]


def _get_embedding(text: str) -> list[float]:
    response = bedrock_rt.invoke_model(
        modelId="amazon.titan-embed-text-v2:0",
        body=json.dumps({"inputText": text[:8000]}),
    )
    return json.loads(response["body"].read())["embedding"]


def _execute_query(cypher: str) -> dict:
    try:
        response = neptune.execute_query(
            graphIdentifier=GRAPH_ID,
            queryString=cypher,
            language="OPEN_CYPHER",
        )
        return json.loads(response["payload"].read())
    except Exception as e:
        return {"error": str(e), "results": []}


@tool
def search_context_graph(query: str) -> str:
    """Search the context graph for entities, relationships, and decision history.

    Use this tool to find WHY things are the way they are — decision traces,
    entity relationships, and historical context. This complements the knowledge
    base which tells you WHAT is true.

    Args:
        query: The search query about entities, decisions, or relationships.

    Returns:
        Relevant entities, their relationships, and any related decision traces.
    """
    embedding = _get_embedding(query)

    # Search entities
    entity_results = _execute_query(f"""
        CALL neptune.algo.vectors.topKByNode({{
            queryVector: {embedding},
            topK: 5
        }})
        YIELD node, score
        WHERE score > 0.3
        OPTIONAL MATCH (node)-[r]-(connected)
        RETURN labels(node) AS type, node.name AS name,
               node.description AS description, score,
               collect(DISTINCT {{
                   relationship: type(r),
                   connected_to: connected.name
               }})[..5] AS connections
        ORDER BY score DESC
    """)

    # Search decisions
    decision_results = _execute_query(f"""
        CALL neptune.algo.vectors.topKByNode({{
            queryVector: {embedding},
            topK: 3,
            nodeLabels: ['Decision', 'DecisionTrace']
        }})
        YIELD node, score
        WHERE score > 0.3
        RETURN labels(node) AS type, node.title AS title,
               node.decision AS decision, node.rationale AS rationale,
               node.context AS context, node.date AS date,
               node.timestamp AS timestamp, score
        ORDER BY score DESC
    """)

    # Format results
    parts = ["## Entities and Relationships"]
    for r in entity_results.get("results", []):
        parts.append(
            f"- [{', '.join(r.get('type', []))}] **{r.get('name', '')}**: "
            f"{r.get('description', 'N/A')}"
        )
        for conn in r.get("connections", []):
            if conn.get("connected_to"):
                parts.append(f"  → {conn['relationship']}: {conn['connected_to']}")

    parts.append("\n## Decision History")
    for r in decision_results.get("results", []):
        title = r.get("title", r.get("decision", "N/A"))
        parts.append(f"- **{title}** ({r.get('date', r.get('timestamp', 'N/A'))})")
        if r.get("context"):
            parts.append(f"  Context: {r['context']}")
        if r.get("rationale"):
            parts.append(f"  Rationale: {r['rationale']}")

    return "\n".join(parts) if len(parts) > 2 else "No relevant context found in the graph."


@tool
def record_decision(
    query: str, reasoning: str, decision: str, entities_considered: str
) -> str:
    """Record an agent decision trace in the context graph for future reference.

    Call this after making a recommendation or decision to capture the reasoning
    for future queries. This builds the 'event clock' — the history of WHY
    decisions were made.

    Args:
        query: The original user question that prompted this decision.
        reasoning: The agent's reasoning process and factors considered.
        decision: The final recommendation or decision made.
        entities_considered: Comma-separated list of entities/topics considered.

    Returns:
        Confirmation that the decision trace was recorded.
    """
    trace_id = f"TRACE-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
    timestamp = datetime.now(timezone.utc).isoformat()
    trace_text = f"{query} {reasoning} {decision}"
    embedding = _get_embedding(trace_text)

    # Escape single quotes
    safe = lambda s: s.replace("'", "").replace("\\", "")

    _execute_query(f"""
        CREATE (t:DecisionTrace {{
            id: '{trace_id}',
            timestamp: '{timestamp}',
            user_query: '{safe(query)}',
            reasoning: '{safe(reasoning)}',
            decision: '{safe(decision)}',
            embedding: {embedding}
        }})
    """)

    # Link to existing entities
    for entity_name in entities_considered.split(","):
        entity_name = entity_name.strip()
        if entity_name:
            _execute_query(f"""
                MATCH (t:DecisionTrace {{id: '{trace_id}'}})
                MATCH (e {{name: '{safe(entity_name)}'}})
                MERGE (t)-[:CONSIDERED]->(e)
            """)

    return (
        f"Decision trace {trace_id} recorded at {timestamp}. "
        f"This reasoning is now available for future queries."
    )


@tool
def ingest_email_decision(email_text: str) -> str:
    """Extract a decision from an email thread and store it in the context graph.

    Use this when you encounter an email that contains a decision about metric
    thresholds, category changes, reconciliation rules, or system configurations.
    The tool uses Claude to extract structured decision data and creates a
    Decision node with relationships in the graph.

    Args:
        email_text: The full email text containing the decision.

    Returns:
        Confirmation of the decision captured with its ID and linked entities.
    """
    # Use Claude to extract structured decision from email
    extract_prompt = (
        "Extract the decision from this email. Return ONLY valid JSON:\n"
        "{\n"
        '  "decision_id": "short-id like DEC-006 or Q4-AUDIT",\n'
        '  "title": "brief title",\n'
        '  "date": "YYYY-MM-DD",\n'
        '  "decided_by": "person name and role",\n'
        '  "decision": "what was decided",\n'
        '  "rationale": "why it was decided",\n'
        '  "impact": "expected impact",\n'
        '  "entities_affected": ["list of metrics, systems, or configs affected"]\n'
        "}\n\n"
        f"Email:\n{email_text[:4000]}"
    )

    response = bedrock_rt.invoke_model(
        modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": extract_prompt}],
        }),
    )
    result = json.loads(response["body"].read())
    content = result["content"][0]["text"]

    # Parse JSON
    start = content.find("{")
    end = content.rfind("}") + 1
    decision = json.loads(content[start:end])

    safe = lambda s: str(s).replace("'", "").replace("\\", "")

    dec_id = safe(decision.get("decision_id", f"EMAIL-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"))
    title = safe(decision.get("title", ""))
    date = safe(decision.get("date", ""))
    decided_by = safe(decision.get("decided_by", ""))
    dec_text = safe(decision.get("decision", ""))
    rationale = safe(decision.get("rationale", ""))
    impact = safe(decision.get("impact", ""))
    entities = decision.get("entities_affected", [])

    # Create embedding for the decision
    embed_text = f"{title}: {dec_text} {rationale} {impact}"
    embedding = _get_embedding(embed_text)

    # Create Decision node in graph
    _execute_query(f"""
        MERGE (d:Decision {{id: '{dec_id}'}})
        ON CREATE SET
            d.title = '{title}',
            d.date = '{date}',
            d.decided_by = '{decided_by}',
            d.decision = '{dec_text}',
            d.rationale = '{rationale}',
            d.impact = '{impact}',
            d.source = 'email',
            d.embedding = {embedding}
    """)

    # Link to affected entities
    linked = []
    for entity_name in entities:
        entity_name = safe(entity_name)
        result = _execute_query(f"""
            MATCH (e {{name: '{entity_name}'}})
            RETURN e.name AS name
        """)
        if result.get("results"):
            _execute_query(f"""
                MATCH (d:Decision {{id: '{dec_id}'}})
                MATCH (e {{name: '{entity_name}'}})
                MERGE (d)-[:AFFECTS]->(e)
            """)
            linked.append(entity_name)
        else:
            # Create entity if it doesn't exist
            _execute_query(f"""
                MERGE (e:Entity {{name: '{entity_name}'}})
            """)
            _execute_query(f"""
                MATCH (d:Decision {{id: '{dec_id}'}})
                MATCH (e:Entity {{name: '{entity_name}'}})
                MERGE (d)-[:AFFECTS]->(e)
            """)
            linked.append(f"{entity_name} (new)")

    return (
        f"Decision captured: {dec_id}\n"
        f"Title: {title}\n"
        f"Date: {date}\n"
        f"Decided by: {decided_by}\n"
        f"Decision: {dec_text}\n"
        f"Rationale: {rationale}\n"
        f"Linked entities: {', '.join(linked)}\n"
        f"Source: email thread"
    )
