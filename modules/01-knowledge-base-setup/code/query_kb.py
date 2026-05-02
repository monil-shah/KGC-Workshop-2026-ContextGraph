"""Query the Bedrock Knowledge Base and optionally show retrieval details."""
import os
import sys
import json
import boto3

bedrock_runtime = boto3.client("bedrock-agent-runtime")

config_path = os.path.join(os.path.dirname(__file__), "..", "..", "kb_config.json")
with open(config_path) as f:
    config = json.load(f)

KB_ID = config["knowledge_base_id"]
MODEL_ARN = (
    "arn:aws:bedrock:us-east-1::foundation-model/"
    "anthropic.claude-3-5-sonnet-20241022-v2:0"
)

verbose = "--verbose" in sys.argv
query = " ".join(arg for arg in sys.argv[1:] if arg != "--verbose")

if not query:
    print("Usage: python query_kb.py [--verbose] <your question>")
    print("Examples:")
    print('  python query_kb.py "What metrics track PO aging?"')
    print('  python query_kb.py "What are the GRC controls for reconciliation?"')
    print('  python query_kb.py --verbose "What is the PO aging threshold?"')
    sys.exit(1)

print(f"🔍 Query: {query}\n")

# Retrieve and Generate
response = bedrock_runtime.retrieve_and_generate(
    input={"text": query},
    retrieveAndGenerateConfiguration={
        "type": "KNOWLEDGE_BASE",
        "knowledgeBaseConfiguration": {
            "knowledgeBaseId": KB_ID,
            "modelArn": MODEL_ARN,
            "retrievalConfiguration": {
                "vectorSearchConfiguration": {"numberOfResults": 5}
            },
        },
    },
)

# Print the generated answer
print("💬 Answer:")
print(response["output"]["text"])

# Print citations
citations = response.get("citations", [])
if citations:
    print(f"\n📚 Sources ({len(citations)} citations):")
    for i, citation in enumerate(citations, 1):
        refs = citation.get("retrievedReferences", [])
        for ref in refs:
            location = ref.get("location", {}).get("s3Location", {})
            uri = location.get("uri", "Unknown")
            print(f"  [{i}] {uri}")

# Verbose: show chunk details
if verbose:
    print("\n" + "=" * 60)
    print("RETRIEVAL DETAILS")
    print("=" * 60)

    retrieve_response = bedrock_runtime.retrieve(
        knowledgeBaseId=KB_ID,
        retrievalQuery={"text": query},
        retrievalConfiguration={
            "vectorSearchConfiguration": {"numberOfResults": 5}
        },
    )

    for i, result in enumerate(retrieve_response["retrievalResults"], 1):
        score = result.get("score", 0)
        text = result.get("content", {}).get("text", "")[:200]
        location = result.get("location", {}).get("s3Location", {}).get("uri", "")
        print(f"\n--- Chunk {i} (score: {score:.4f}) ---")
        print(f"Source: {location}")
        print(f"Text: {text}...")
