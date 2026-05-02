# Module 5: Putting It All Together

**Duration**: ~45 minutes

## What You'll Build

A complete **Agentic RAG** system that combines everything from the previous modules:

- **Bedrock Knowledge Base** with custom chunking (Module 1 & 2)
- **Strands Agent** with custom tools (Module 3)
- **Neptune Analytics Context Graph** (Module 4)

The agent will:
1. Search the knowledge base for relevant information
2. Query the context graph for relationships and decision history
3. Record its own decision traces for future reference
4. Provide answers grounded in both *what is true* and *why*

## Architecture

```
                    User Query
                        │
                ┌───────▼────────┐
                │  Strands Agent │
                │  (Orchestrator)│
                └──┬──────┬──┬──┘
                   │      │  │
         ┌─────────▼┐  ┌──▼──▼──────────┐
         │ retrieve  │  │ graph_search   │
         │ (KB tool) │  │ (Neptune tool) │
         └─────┬─────┘  └───────┬────────┘
               │                │
     ┌─────────▼─────┐  ┌──────▼──────────┐
     │  Bedrock KB   │  │ Neptune Analytics│
     │  (OpenSearch)  │  │ (Graph+Vector)  │
     └───────────────┘  └─────────────────┘
               │                │
               └────────┬───────┘
                        │
                ┌───────▼────────┐
                │ record_decision│
                │ (trace tool)   │
                └───────┬────────┘
                        │
                ┌───────▼────────┐
                │  Final Answer  │
                │  (What + Why)  │
                └────────────────┘
```

## Step 1: Run the Integrated Agent

```bash
python code/integrated_agent.py
```

This creates a Strands agent with three custom tools:
- `search_knowledge_base` — Retrieves from Bedrock KB
- `search_context_graph` — Queries Neptune for entities, relationships, and decisions
- `record_decision` — Captures the agent's reasoning as a decision trace

## Step 2: Interactive Session

```bash
python code/interactive.py
```

Chat with the fully integrated agent. Try questions that exercise all three capabilities:

```
> What compute service should I use for a batch processing job?
  (KB retrieval + graph search + decision recording)

> Why did we choose DynamoDB for user preferences?
  (Graph search for decision traces)

> A new engineer is starting Monday — what do they need?
  (KB retrieval for onboarding + graph for related policies)

> We had a partial outage affecting 15% of users. What do we do?
  (KB for incident response + graph for past decisions + severity classification)
```

## Step 3: Examine the Decision Trail

```bash
python code/show_decisions.py
```

This visualizes all decision traces captured during your session, showing how the agent's reasoning is preserved in the graph.

## Step 4: Evaluate the System

```bash
python code/evaluate.py
```

Runs a set of test queries and compares:
- **KB-only answers** (what)
- **Graph-enhanced answers** (what + why)
- **Response quality** (completeness, accuracy, context)

## What Makes This Different from Standard RAG

| Capability | Standard RAG | This System |
|-----------|-------------|-------------|
| Find relevant text | ✅ | ✅ |
| Cite sources | ✅ | ✅ |
| Explain decisions | ❌ | ✅ (decision traces) |
| Show relationships | ❌ | ✅ (graph traversal) |
| Learn from past interactions | ❌ | ✅ (recorded traces) |
| Multi-hop reasoning | ❌ | ✅ (graph paths) |
| Temporal context | ❌ | ✅ (when + why) |

## Key Takeaways

- Combining KB + Graph gives agents both the **state clock** and **event clock**
- Decision traces make agent reasoning **transparent and auditable**
- The graph grows over time, making the system **smarter with use**
- Strands makes it easy to wire these capabilities together as tools
- This pattern applies to any domain: legal, medical, engineering, compliance

## Cleanup

When you're done, remove all workshop resources:

```bash
cd ../../
./infrastructure/scripts/cleanup.sh agentic-rag-workshop us-east-1
```

## What's Next?

Ideas for extending this workshop:
- Add **guardrails** to the agent (Bedrock Guardrails)
- Implement **session memory** with Strands session managers
- Add **evaluation metrics** (RAGAS framework)
- Deploy the agent as an **API** (Lambda + API Gateway)
- Add **multi-modal** support (documents with images)
