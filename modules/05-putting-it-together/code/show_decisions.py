"""Show all decision traces captured in the context graph."""
import os
import json
import boto3
from rich.console import Console
from rich.panel import Panel

console = Console()
neptune = boto3.client("neptune-graph")

config_path = os.path.join(os.path.dirname(__file__), "..", "..", "kb_config.json")
with open(config_path) as f:
    config = json.load(f)

GRAPH_ID = config["neptune_graph_id"]

console.print("\n[bold]📝 Decision Traces in Context Graph[/]\n")

response = neptune.execute_query(
    graphIdentifier=GRAPH_ID,
    queryString="""
        MATCH (t:DecisionTrace)
        OPTIONAL MATCH (t)-[r:CONSIDERED]->(e)
        RETURN t.id AS id, t.timestamp AS timestamp,
               t.user_query AS query, t.reasoning AS reasoning,
               t.decision AS decision,
               collect(e.name) AS entities_considered
        ORDER BY t.timestamp DESC
    """,
    language="OPEN_CYPHER",
)

results = json.loads(response["payload"].read())
traces = results.get("results", [])

if not traces:
    console.print("[dim]No decision traces found. Run the integrated agent first.[/]")
else:
    console.print(f"Found {len(traces)} decision trace(s):\n")
    for trace in traces:
        entities = ", ".join(trace.get("entities_considered", [])) or "None"
        console.print(Panel(
            f"[bold]Query:[/] {trace.get('query', 'N/A')}\n\n"
            f"[bold]Reasoning:[/] {trace.get('reasoning', 'N/A')}\n\n"
            f"[bold]Decision:[/] {trace.get('decision', 'N/A')}\n\n"
            f"[bold]Entities Considered:[/] {entities}\n"
            f"[dim]Timestamp: {trace.get('timestamp', 'N/A')}[/]",
            title=f"🔍 {trace.get('id', 'Unknown')}",
            border_style="green",
        ))
