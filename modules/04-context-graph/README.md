# Module 4: Context Graph — Solving the Two Clock Problem

**Duration**: ~45 minutes

## What You'll Build

A **context graph** using **Amazon Neptune Analytics** that captures:
- Entity relationships extracted from your knowledge base
- Decision traces from agent interactions
- Temporal context (when things changed and why)

This solves the **two clock problem** — giving your agent access to both *what is true* and *why it became true*.

## The Two Clock Problem

Every enterprise has two types of knowledge:

| | State Clock | Event Clock |
|---|---|---|
| **Question** | What is true right now? | Why did it become true? |
| **Example** | "MFA is mandatory" | "MFA was mandated after the 2024 security audit" |
| **Infrastructure** | Databases, knowledge bases | Almost nothing (the gap!) |
| **AI Impact** | Agent knows the current policy | Agent can explain the reasoning |

Traditional RAG only gives agents the **state clock**. When a user asks "Why do we require 14-character passwords?", the agent can quote the policy but can't explain the decision behind it.

**Context graphs fill this gap** by capturing decision traces as first-class data.

## Architecture

```
┌─────────────────────────────────────────────────┐
│              Neptune Analytics                   │
│                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │ Document  │───▶│  Entity  │◀───│ Decision │  │
│  │  Nodes    │    │  Nodes   │    │  Traces  │  │
│  └──────────┘    └──────────┘    └──────────┘  │
│       │               │               │         │
│       │          ┌────▼────┐          │         │
│       └─────────▶│ Vector  │◀─────────┘         │
│                  │ Index   │                     │
│                  └─────────┘                     │
│                                                  │
│  Hybrid Query: Vector Search + Graph Traversal   │
└─────────────────────────────────────────────────┘
```

## Step 1: Create the Neptune Analytics Graph

```bash
python code/create_graph.py
```

This creates a Neptune Analytics graph with vector search enabled. The graph will store:
- **Document nodes**: Source documents from your KB
- **Entity nodes**: People, policies, services, concepts extracted from documents
- **Decision nodes**: Architecture decisions, policy changes with rationale
- **Relationship edges**: How entities relate to each other

## Step 2: Build the Knowledge Graph

```bash
python code/populate_graph.py
```

This script:
1. Reads your source documents
2. Uses Claude to extract entities and relationships
3. Creates nodes and edges in Neptune Analytics
4. Generates vector embeddings for graph-based semantic search

## Step 3: Query the Graph

```bash
python code/query_graph.py "Why do we require 14-character passwords?"
```

Compare the results:
- **Vector-only** (from Module 1): Returns the policy text
- **Graph-enhanced**: Returns the policy text + the decision trace + related entities

Try more queries:
```bash
python code/query_graph.py "What led to the adoption of Bedrock?"
python code/query_graph.py "How are DynamoDB and the user preferences service related?"
python code/query_graph.py "What changed after the 2024 security audit?"
```

## Step 4: Capture Decision Traces

```bash
python code/add_decision_trace.py
```

This demonstrates how to record agent decisions as graph nodes:
- What was the input?
- What knowledge was retrieved?
- What reasoning was applied?
- What was the output?
- When did this happen?

These traces become searchable context for future interactions.

## Step 5: Hybrid Retrieval (Vector + Graph)

```bash
python code/hybrid_retrieval.py "What compute services should I use for a new microservice?"
```

This combines:
1. **Vector search**: Find semantically similar content
2. **Graph traversal**: Follow relationships to find connected context
3. **Reciprocal Rank Fusion**: Merge and re-rank results from both sources

## How GraphRAG Works

```
Query: "Why do we use DynamoDB for user preferences?"

Vector Search (similarity):              Graph Traversal (relationships):
┌─────────────────────────┐              ┌─────────────────────────┐
│ "DynamoDB single-table  │              │ ADR-001 ──decides──▶    │
│  design with on-demand  │              │   DynamoDB              │
│  capacity"              │              │     │                   │
│                         │              │   ──reason──▶           │
│ Score: 0.92             │              │   "Simpler operations,  │
└─────────────────────────┘              │    automatic scaling"   │
                                         │     │                   │
                                         │   ──context──▶          │
                                         │   "User preferences are │
                                         │    key-value lookups    │
                                         │    with <10ms latency"  │
                                         └─────────────────────────┘

Fused Result: Full decision context with both WHAT and WHY
```

## Key Takeaways

- The **two clock problem** is the gap between knowing what's true and why it's true
- **Context graphs** capture decision traces, entity relationships, and temporal context
- **Neptune Analytics** provides hybrid vector + graph queries in a single engine
- **GraphRAG** combines vector similarity with graph traversal for richer retrieval
- Decision traces make your agent's reasoning transparent and auditable

## Next

→ [Module 5: Putting It All Together](../05-putting-it-together/) — Wire KB + Agent + Graph into a complete system
