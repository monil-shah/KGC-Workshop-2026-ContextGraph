# Building Agentic RAG with Context Graph on AWS

> Hands-on workshop — 90 minutes
>
> Knowledge Bases • Context Graphs • Agentic AI

---

## The Story

AWS CapEx FBI, Accounting, and Finance teams manage **$18B+ in infrastructure transactions** annually flowing through Veritas automation. Today, reconciling these transactions across SC.os, AP, OFA, FASL+, and AFS is fragmented, partially manual, and critical decision context is lost every quarter.

This workshop builds an **AI-powered Metrics Assistant** that solves three real problems:

| Problem | Root Cause | Solution |
|---------|-----------|----------|
| Partial, misleading answers | Fixed-size chunking splits metric definitions mid-definition | **Custom chunking** that preserves namespace/metric structure |
| "I don't know why" | No record of WHY thresholds were set or changed | **Context graph** capturing decisions from docs, agents, and emails |
| "I can answer but can't act" | RAG is a search engine, not an assistant | **Strands agent** with tools that classify risk, check controls, and record decisions |

---

## Concepts Explained

### What is RAG (Retrieval-Augmented Generation)?

RAG connects an LLM to your data. Instead of relying on training data alone, the LLM retrieves relevant documents at query time and uses them as context to generate grounded answers with citations.

```
Question → Embed → Vector Search → Top-K Chunks → LLM + Chunks → Answer
```

**The problem**: Standard RAG treats all documents the same. A 300-token fixed-size chunk doesn't care if it splits a metric definition in half. Custom chunking fixes this by splitting on logical boundaries (namespaces, sections, JSON blocks) and adding metadata.

### What is the Two Clock Problem?

Every organization has two types of knowledge:

- **State Clock** — What is true right now. "The PO aging threshold is 90 days." Your knowledge base handles this.
- **Event Clock** — Why it became true. "Changed from 60 to 90 days after Q4 2024 audit found 40% false positives." Almost no infrastructure exists for this.

Standard RAG only gives agents the state clock. When someone asks "Why is the threshold 90 days?", the agent can quote the config but can't explain the decision. **Context graphs** solve this by storing decisions, relationships, and temporal context as graph nodes — searchable alongside your documents.

### What is GraphRAG?

GraphRAG combines two retrieval strategies:

- **Vector search** finds semantically similar text (what's relevant)
- **Graph traversal** follows relationships between entities (what's connected)

These are fused using **Reciprocal Rank Fusion (RRF)**: `score = Σ 1/(k + rank)` across both result sets. The most relevant answer isn't always the most similar text — sometimes it's the decision node three hops away in the graph.

### What is Agentic AI?

An agent is an LLM with tools. Instead of just generating text, it can:
1. Decide which tool to call (retrieve from KB, query graph, classify risk)
2. Execute the tool and read the result
3. Decide if it needs more information or can answer
4. Loop until it has a complete answer

**Strands Agents SDK** makes this simple: you decorate Python functions with `@tool`, give them to an `Agent()`, and the LLM handles orchestration.

### What are Decision Traces?

Every time the agent makes a recommendation, it records:
- What was asked
- What was retrieved
- What reasoning was applied
- What was decided
- When it happened

These traces become searchable graph nodes. Next quarter, when someone asks the same question, the agent finds the precedent — like case law for financial operations.

### Why Capture Decisions from Emails?

Most financial decisions happen in email threads: threshold approvals, category reclassifications, audit findings. These are the richest source of "event clock" data, but they're trapped in inboxes. The `ingest_email_decision` tool extracts structured decisions from emails using Claude and stores them in the context graph.

---

## Architecture

```
              "What POs are aging >90 days for EMEA?"
                              │
                      ┌───────▼────────┐
                      │  Strands Agent  │
                      │  (AFS Metrics   │
                      │   Assistant)    │
                      └──┬───┬───┬───┬─┘
                         │   │   │   │
               ┌─────────▼┐ ┌▼───▼┐ ┌▼──────────────┐
               │ retrieve  │ │graph│ │ingest_email_  │
               │ (KB)      │ │tools│ │decision       │
               └─────┬─────┘ └──┬──┘ └──────┬────────┘
                     │          │            │
            ┌────────▼────┐ ┌───▼──────────┐ │
            │  Bedrock KB │ │   Neptune    │◀┘
            │  (OpenSearch │ │   Analytics  │
            │  Serverless) │ │(Context Graph│
            └─────┬───────┘ └──────────────┘
                  │
       ┌──────────▼──────────────────┐
       │  S3 → Custom Chunking Lambda │
       │  → Titan Embeddings V2       │
       │  → OpenSearch Vector Index   │
       └─────────────────────────────┘
```

**AWS Services Used**:
- Amazon Bedrock (Claude Sonnet, Titan Embeddings V2, Knowledge Bases)
- Amazon OpenSearch Serverless (vector store)
- Amazon Neptune Analytics (graph + vector hybrid)
- AWS Lambda (custom chunking)
- Amazon S3 (document storage)

---

## Prerequisites

- AWS account with admin access
- AWS CLI v2 configured (`aws configure`)
- Node.js 18+ and Python 3.12+
- Bedrock model access enabled for **Claude 3.5 Sonnet** and **Titan Embeddings V2**

---

## Setup (10 minutes)

### Step 1: Clone and deploy infrastructure

```bash
git clone https://github.com/YOUR_ORG/agentic-rag-workshop.git
cd agentic-rag-workshop

# Deploy with CDK (creates S3, OpenSearch Serverless, IAM roles)
cd infrastructure/cdk
npm install
npx cdk bootstrap          # first time only
npx cdk deploy             # ~5 min for OpenSearch collection
cd ../..
```

### Step 2: Set up Python

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 3: Load environment variables

```bash
source infrastructure/scripts/get-outputs.sh
```

This exports `WORKSHOP_BUCKET`, `OPENSEARCH_COLLECTION_ARN`, `KB_ROLE_ARN`, `LAMBDA_ROLE_ARN`.

---

## Module 1: Knowledge Base + Custom Chunking (30 min)

> **Concept**: Standard RAG uses fixed-size chunking (e.g., 300 tokens with 20% overlap). This is fast but dumb — it doesn't care if it splits a metric definition in half. Custom chunking preserves document structure and adds metadata so the right context is always retrieved intact.
>
> **What we solve**: The AFS metric definition for `po_aging_not_invoiced` includes type, filters, dimensions, and periods. Fixed-size chunking splits this across two chunks — the agent returns a partial answer missing the 90-day threshold. Custom chunking keeps the entire definition as one chunk with namespace metadata.

### Step 1: Upload AFS documents to S3

```bash
cd modules/01-knowledge-base-setup/code
python upload_documents.py
```

Uploads 5 documents: metric definitions (14 P0 metrics across 3 namespaces), reconciliation rules, namespace JSON configs, compliance policies, and decision emails.

### Step 2: Create the Knowledge Base

```bash
python create_knowledge_base.py
```

Creates a Bedrock KB with:
- **Titan Embeddings V2** (1024-dim vectors)
- **OpenSearch Serverless** as the vector store
- **Fixed-size chunking** (300 tokens, 20% overlap) — the baseline we'll improve

Watch the ingestion progress: `STARTING → IN_PROGRESS → COMPLETE`.

### Step 3: Query — see the problem

```bash
python query_kb.py "What metrics track PO aging for the LLE category?"
python query_kb.py --verbose "What is the PO aging threshold?"
```

The `--verbose` flag shows retrieved chunks and similarity scores. Notice how fixed-size chunking may split metric definitions.

### Step 4: Compare chunking strategies

```bash
cd ../../02-custom-chunking/code
python compare_chunking.py
```

Side-by-side comparison of how the same document gets split by:
- **Fixed-size** (300 tokens) — ignores structure
- **Semantic** (NLP topic boundaries) — respects paragraphs
- **Hierarchical** (parent/child) — multi-granularity
- **Custom Lambda** (namespace-aware) — preserves metric definitions with metadata

### Step 5: Deploy the custom chunker

```bash
python deploy_custom_chunker.py
```

Deploys a Lambda function that:
- Splits on namespace and metric definition boundaries
- Tracks `namespace`, `metric_name`, `doc_type` in metadata
- Keeps JSON configs and tables as atomic units

### Step 6: Create custom-chunked data source and compare

```bash
python create_custom_datasource.py
python evaluate_chunking.py "What metrics track PO aging for the LLE category?"
```

Now the agent retrieves the complete `po_aging_not_invoiced` definition with all filters, dimensions, and periods.

---

## Module 2: Context Graph (30 min)

> **Concept**: A context graph stores entities (systems, metrics, decisions) and their relationships in a graph database. Combined with vector search, this enables **GraphRAG** — hybrid retrieval that finds both similar text AND connected context. This is the "event clock" that captures WHY things are the way they are.
>
> **What we solve**: When someone asks "Why is the PO aging threshold 90 days?", the KB can only quote the current config. The context graph stores the Q4-2024-AUDIT decision node with rationale ("60-day generated 40% false positives"), the person who approved it (Sarah Chen), and links to affected metrics.

### Step 1: Create the Neptune Analytics graph

```bash
cd ../../04-context-graph/code
python create_graph.py
```

Creates a Neptune Analytics graph (32 GB) with vector search enabled (1024-dim, matching Titan Embeddings). Takes 5-10 minutes to provision.

### Step 2: Extract entities and populate the graph

```bash
python populate_graph.py
```

Uses Claude to extract from your AFS documents:
- **System nodes**: SC.os, AP, OFA, FASL+, AFS, Veritas
- **Metric nodes**: po_total_spend, failed_asset_creates, etc.
- **Namespace nodes**: veritas_po_metrics, afs_asset_metrics
- **Decision nodes**: DEC-001 through DEC-005 with rationale
- **Relationship edges**: FEEDS_INTO, DEFINES, HAS_DIMENSION, DECIDED, CAUSED_BY

### Step 3: Query the graph — vector + graph hybrid

```bash
python query_graph.py "Why was the PO aging threshold changed from 60 to 90 days?"
```

Compare what you get:
- **Vector search**: Returns text about "90-day threshold" (WHAT)
- **Graph traversal**: Returns Decision Q4-2024-AUDIT → DECIDED → 90 days, CAUSED_BY → "40% false positives" (WHY)
- **Decision traces**: Shows who approved it and when

### Step 4: Record a decision trace

```bash
python add_decision_trace.py
```

Simulates a month-end close scenario: classifying 47 EMEA POs as HIGH/LOW risk. The agent's reasoning is stored as a `DecisionTrace` node linked to `po_aging_not_invoiced` and `EMEA` entities.

### Step 5: Hybrid retrieval (RRF fusion)

```bash
python hybrid_retrieval.py "What metrics should I check for month-end close and why were the thresholds set this way?"
```

Combines KB vector search + Neptune graph search using Reciprocal Rank Fusion. The result includes both current metric definitions AND the decisions that shaped them.

---

## Module 3: Agentic AI with Strands (30 min)

> **Concept**: An agent is an LLM with tools. The **Strands Agents SDK** uses a model-driven approach: you give the LLM tools (Python functions decorated with `@tool`) and it decides when to call them. The agent loop runs until the LLM has enough information to answer.
>
> **What we solve**: The AFS assistant can now answer questions AND take action — classify risk levels, check GRC controls, record decisions, and capture decisions from email threads. It's an assistant, not a search engine.

### Step 1: Simple agent with KB retrieval

```bash
cd ../../03-strands-agent/code
python simple_agent.py
```

Creates a minimal agent:
```python
agent = Agent(model=BedrockModel(), tools=[retrieve])
agent("What metrics track PO aging for the LLE category?")
```

The agent automatically calls the `retrieve` tool, reads the chunks, and generates a grounded answer.

### Step 2: Add custom tools

```bash
python agent_with_tools.py
```

Adds three AFS-specific tools:
- `classify_risk(po_count, total_amount, aging_days)` — classifies HIGH/MEDIUM/LOW risk
- `get_period_info()` — returns current accounting period and close deadlines
- `check_grc_control(control_id)` — looks up GRC control details

The LLM decides which tools to call based on the question.

### Step 3: Multi-agent system

```bash
python multi_agent.py
```

Creates specialist agents (metrics, reconciliation, compliance) wrapped as tools for a router agent. The router classifies the question and delegates to the right specialist.

### Step 4: Full integrated agent

```bash
cd ../../05-putting-it-together/code
python integrated_agent.py
```

The complete AFS Metrics Assistant with four tools:

| Tool | Source | Purpose |
|------|--------|---------|
| `retrieve` | Bedrock KB | Current metric definitions, rules, policies (state clock) |
| `search_context_graph` | Neptune Analytics | Decision history, system relationships (event clock) |
| `record_decision` | Neptune write | Captures agent reasoning as audit trail |
| `ingest_email_decision` | Claude + Neptune | Extracts decisions from email threads into the graph |

Demo flow:
1. "What metrics track PO aging?" → KB retrieval
2. "Classify risk on 47 EMEA POs totaling $3.2M" → classify + record
3. Paste an email → `ingest_email_decision` extracts and stores the decision
4. "What decisions about PO aging?" → graph finds the email decision

### Step 5: Interactive chat

```bash
python interactive.py
```

Chat with the full system. Try the month-end close scenario:

```
You: What metrics should I review for month-end close?
You: Why is the PO aging threshold 90 days and not 60?
You: We have 47 EMEA POs aging >90 days totaling $3.2M. Classify the risk.
You: [paste an email about a threshold change] Capture this decision.
You: What decisions have been made about PO aging thresholds?
```

### Step 6: View decision traces

```bash
python show_decisions.py
```

Visualizes all decision traces captured during your session.

### Step 7: Evaluate KB-only vs graph-enhanced

```bash
python evaluate.py
```

Side-by-side comparison showing how graph-enhanced answers include decision context that KB-only answers miss.

---

## Cleanup

Remove all workshop resources:

```bash
cd ../../../
./infrastructure/scripts/cleanup.sh us-east-1
```

This deletes: Bedrock KB, Neptune graph, custom chunker Lambda, S3 contents, and the CDK stack.

**Estimated cost for 90 minutes**: $10–15 USD.

---

## Project Structure

```
agentic-rag-workshop/
├── README.md
├── requirements.txt
├── LICENSE                          # MIT-0
├── workshop-slides.pptx             # 28-slide presentation
│
├── infrastructure/
│   ├── cdk/                         # CDK TypeScript (primary)
│   │   ├── bin/app.ts
│   │   ├── lib/workshop-stack.ts    # S3, OpenSearch, IAM, custom resource
│   │   ├── lambda/create-index/     # OpenSearch index creation
│   │   └── package.json
│   ├── cfn/main.yaml                # CloudFormation (alternative)
│   └── scripts/
│       ├── get-outputs.sh           # Export stack outputs as env vars
│       └── cleanup.sh               # Delete all resources
│
├── modules/
│   ├── 01-knowledge-base-setup/
│   │   ├── data/                    # AFS sample documents
│   │   │   ├── metric-definitions.md
│   │   │   ├── reconciliation-rules.md
│   │   │   ├── namespace-configs.md
│   │   │   ├── compliance-policies.md
│   │   │   └── decision-emails.md
│   │   └── code/
│   │       ├── upload_documents.py
│   │       ├── create_knowledge_base.py
│   │       └── query_kb.py
│   │
│   ├── 02-custom-chunking/
│   │   └── code/
│   │       ├── compare_chunking.py
│   │       ├── create_semantic_datasource.py
│   │       ├── create_hierarchical_datasource.py
│   │       ├── deploy_custom_chunker.py
│   │       ├── create_custom_datasource.py
│   │       └── evaluate_chunking.py
│   │
│   ├── 03-strands-agent/
│   │   └── code/
│   │       ├── simple_agent.py
│   │       ├── agent_with_tools.py
│   │       ├── multi_agent.py
│   │       └── chat.py
│   │
│   ├── 04-context-graph/
│   │   └── code/
│   │       ├── create_graph.py
│   │       ├── populate_graph.py
│   │       ├── query_graph.py
│   │       ├── add_decision_trace.py
│   │       └── hybrid_retrieval.py
│   │
│   └── 05-putting-it-together/
│       └── code/
│           ├── tools/
│           │   └── graph_tools.py   # search_context_graph, record_decision, ingest_email_decision
│           ├── integrated_agent.py
│           ├── interactive.py
│           ├── show_decisions.py
│           └── evaluate.py
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `KNOWLEDGE_BASE_ID` not found | Run `source infrastructure/scripts/get-outputs.sh` |
| Bedrock `AccessDeniedException` | Enable model access in Bedrock console for Claude Sonnet + Titan Embeddings V2 |
| Neptune graph stuck on `CREATING` | Normal — first creation takes 5-10 minutes |
| OpenSearch index errors after deploy | Wait 2-3 minutes for collection to become active |
| `ModuleNotFoundError: strands` | Activate venv: `source .venv/bin/activate` |
| CDK bootstrap error | Run `npx cdk bootstrap` once per account/region |

---

## License

MIT-0 — See [LICENSE](LICENSE)
