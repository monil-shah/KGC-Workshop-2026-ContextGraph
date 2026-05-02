"""Create a Bedrock Knowledge Base with OpenSearch Serverless vector store."""
import os
import json
import time
import boto3

bedrock_agent = boto3.client("bedrock-agent")

KB_ROLE_ARN = os.environ["KB_ROLE_ARN"]
COLLECTION_ARN = os.environ["OPENSEARCH_COLLECTION_ARN"]
BUCKET = os.environ["WORKSHOP_BUCKET"]
INDEX_NAME = "workshop-kb-index"

# Step 1: Create the Knowledge Base
print("Creating Knowledge Base...")
kb_response = bedrock_agent.create_knowledge_base(
    name="workshop-kb",
    description="Workshop Knowledge Base with default chunking",
    roleArn=KB_ROLE_ARN,
    knowledgeBaseConfiguration={
        "type": "VECTOR",
        "vectorKnowledgeBaseConfiguration": {
            "embeddingModelArn": (
                "arn:aws:bedrock:us-east-1::foundation-model/"
                "amazon.titan-embed-text-v2:0"
            ),
        },
    },
    storageConfiguration={
        "type": "OPENSEARCH_SERVERLESS",
        "opensearchServerlessConfiguration": {
            "collectionArn": COLLECTION_ARN,
            "vectorIndexName": INDEX_NAME,
            "fieldMapping": {
                "vectorField": "embedding",
                "textField": "text",
                "metadataField": "metadata",
            },
        },
    },
)

kb_id = kb_response["knowledgeBase"]["knowledgeBaseId"]
print(f"Knowledge Base created: {kb_id}")

# Step 2: Create the S3 Data Source (default chunking)
print("Creating data source...")
ds_response = bedrock_agent.create_data_source(
    knowledgeBaseId=kb_id,
    name="workshop-documents",
    dataSourceConfiguration={
        "type": "S3",
        "s3Configuration": {"bucketArn": f"arn:aws:s3:::{BUCKET}"},
    },
    vectorIngestionConfiguration={
        "chunkingConfiguration": {
            "chunkingStrategy": "FIXED_SIZE",
            "fixedSizeChunkingConfiguration": {
                "maxTokens": 300,
                "overlapPercentage": 20,
            },
        }
    },
)

ds_id = ds_response["dataSource"]["dataSourceId"]
print(f"Data source created: {ds_id}")

# Step 3: Start ingestion
print("Starting ingestion job...")
job = bedrock_agent.start_ingestion_job(
    knowledgeBaseId=kb_id, dataSourceId=ds_id
)
job_id = job["ingestionJob"]["ingestionJobId"]

while True:
    status = bedrock_agent.get_ingestion_job(
        knowledgeBaseId=kb_id, dataSourceId=ds_id, ingestionJobId=job_id
    )
    state = status["ingestionJob"]["status"]
    print(f"  Ingestion status: {state}")
    if state in ("COMPLETE", "FAILED"):
        break
    time.sleep(5)

if state == "COMPLETE":
    stats = status["ingestionJob"].get("statistics", {})
    print(f"\n✅ Ingestion complete!")
    print(f"   Documents scanned: {stats.get('numberOfDocumentsScanned', 'N/A')}")
    print(f"   Documents indexed: {stats.get('numberOfNewDocumentsIndexed', 'N/A')}")
else:
    print(f"\n❌ Ingestion failed. Check CloudWatch logs for details.")

# Save KB ID for later modules
config = {"knowledge_base_id": kb_id, "data_source_id": ds_id}
config_path = os.path.join(os.path.dirname(__file__), "..", "..", "kb_config.json")
with open(config_path, "w") as f:
    json.dump(config, f, indent=2)
print(f"\nSaved KB config to kb_config.json")
