# Module 2: Custom Chunking Strategies

**Duration**: ~45 minutes

## What You'll Build

Four different chunking strategies for your Knowledge Base, then compare their retrieval quality:

1. **Fixed-size** — Simple token-count splits (baseline from Module 1)
2. **Semantic** — NLP-based splitting at topic boundaries
3. **Hierarchical** — Parent/child chunks for multi-granularity retrieval
4. **Custom Lambda** — Your own chunking logic with metadata enrichment

## Why Chunking Matters

Chunking is the most impactful tuning knob in RAG. Poor chunking leads to:
- **Too small**: Chunks lack context, retrieval returns fragments
- **Too large**: Chunks dilute relevance, embedding quality drops
- **Wrong boundaries**: Chunks split mid-thought, breaking semantic coherence

```
Document: "PO aging threshold: 90 days. | Filters: po_amount > 300, line_category IN [AHU, GENERATOR]"
                                        ^
                                        Bad split here loses the connection
                                        between threshold and filters
```

## Step 1: Compare Chunking Strategies

Run the comparison script to see how each strategy chunks the same document:

```bash
python code/compare_chunking.py
```

This shows you side-by-side how the same document gets split differently.

## Step 2: Create a Semantic Chunking Data Source

```bash
python code/create_semantic_datasource.py
```

Semantic chunking uses an embedding model to detect topic boundaries. It's more expensive (extra FM calls during ingestion) but produces more coherent chunks.

## Step 3: Create a Hierarchical Chunking Data Source

```bash
python code/create_hierarchical_datasource.py
```

Hierarchical chunking creates parent and child chunks. During retrieval, child chunks are matched first, then replaced by their parent for broader context.

## Step 4: Deploy the Custom Chunking Lambda

This is the most powerful option — you write the chunking logic yourself.

```bash
python code/deploy_custom_chunker.py
```

Our custom chunker:
- Splits on markdown headers (preserving document structure)
- Enriches each chunk with metadata (section title, document name, keywords)
- Handles tables and code blocks as atomic units

## Step 5: Create a Custom Lambda Data Source

```bash
python code/create_custom_datasource.py
```

## Step 6: Compare Retrieval Quality

```bash
python code/evaluate_chunking.py "What metrics track PO aging for the LLE category?"
```

This queries all four data sources with the same question and compares:
- Number of relevant chunks retrieved
- Chunk coherence (do chunks contain complete thoughts?)
- Answer quality from each strategy

## How Custom Lambda Chunking Works

```
S3 Document
    │
    ▼
Bedrock Parses Document → Raw Text
    │
    ▼
Your Lambda Function
    ├── Reads parsed text from S3
    ├── Applies your chunking logic
    ├── Adds metadata to each chunk
    ├── Writes chunks back to S3
    └── Returns chunk references
    │
    ▼
Bedrock Embeds Chunks → Vector Store
```

### Lambda Input Format
```json
{
  "inputFiles": [{
    "contentBatches": [{
      "key": "s3://bucket/parsed-content.json"
    }]
  }]
}
```

### Lambda Output Format
```json
{
  "outputFiles": [{
    "key": "s3://bucket/chunked-output.json"
  }]
}
```

## Key Takeaways

- **Fixed-size** is the simplest but ignores document structure
- **Semantic** respects topic boundaries but costs more during ingestion
- **Hierarchical** gives you multi-granularity retrieval
- **Custom Lambda** gives full control — best for structured documents (metric definitions, JSON configs, financial docs)
- Chunking strategy **cannot be changed** after data source creation — choose wisely

## Next

→ [Module 3: Strands Agent](../03-strands-agent/) — Build an AI agent that uses your Knowledge Base
