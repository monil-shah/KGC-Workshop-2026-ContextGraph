# Module 1: Knowledge Base Setup

**Duration**: ~30 minutes

## What You'll Build

An Amazon Bedrock Knowledge Base backed by:
- **Amazon S3** as the document source
- **Amazon OpenSearch Serverless** as the vector store
- **Amazon Titan Embeddings V2** for generating embeddings

## Concepts

A **Knowledge Base** in Amazon Bedrock connects your data to foundation models. The pipeline:

```
Documents (S3) → Parsing → Chunking → Embedding → Vector Store (OpenSearch)
```

When you query the KB, Bedrock:
1. Embeds your query using the same model
2. Performs vector similarity search in OpenSearch
3. Returns the most relevant chunks with source attribution

## Prerequisites

Make sure you've deployed the infrastructure stack and loaded environment variables:

```bash
source infrastructure/scripts/get-outputs.sh agentic-rag-workshop us-east-1
```

## Step 1: Explore the Sample Data

We've included sample documents about AFS financial operations — metric definitions, reconciliation rules, namespace configurations, and compliance policies.

```bash
ls data/
```

You should see markdown files covering metric definitions, reconciliation rules, namespace configs, and compliance policies.

## Step 2: Upload Documents to S3

```bash
python code/upload_documents.py
```

This uploads all documents from `data/` to the S3 bucket created by the CloudFormation stack.

## Step 3: Create the Knowledge Base

```bash
python code/create_knowledge_base.py
```

This script:
1. Creates a Bedrock Knowledge Base with Titan Embeddings V2
2. Connects it to the OpenSearch Serverless collection (already provisioned)
3. Creates a data source pointing to your S3 bucket
4. Starts an ingestion job to process the documents

Watch the output — you'll see the ingestion job progress through `STARTING → IN_PROGRESS → COMPLETE`.

## Step 4: Query the Knowledge Base

```bash
python code/query_kb.py "What metrics track PO aging for the LLE category?"
```

Try a few queries:
```bash
python code/query_kb.py "What are the GRC controls for reconciliation?"
python code/query_kb.py "What is the PO to receipt matching tolerance?"
python code/query_kb.py "What are the month-end close deadlines?"
```

## Step 5: Examine the Retrieval Results

```bash
python code/query_kb.py --verbose "What is the PO aging threshold and why?"
```

The `--verbose` flag shows you:
- The retrieved chunks and their similarity scores
- Source document attribution
- Chunk metadata

## What's Happening Under the Hood

```
Your Query
    │
    ▼
Titan Embeddings V2 (embed query)
    │
    ▼
OpenSearch Serverless (k-NN search, top 5)
    │
    ▼
Retrieved Chunks + Scores
    │
    ▼
Claude Sonnet (generate answer with context)
    │
    ▼
Response with Citations
```

## Key Takeaways

- Bedrock KB handles the entire RAG pipeline: parsing, chunking, embedding, retrieval
- OpenSearch Serverless provides a fully managed vector store with no cluster management
- Default chunking uses fixed-size (300 tokens, 20% overlap) — we'll improve this in Module 2

## Next

→ [Module 2: Custom Chunking](../02-custom-chunking/) — Implement smarter chunking strategies
