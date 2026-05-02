"""Create a data source with hierarchical chunking strategy."""
import os
import json
import time
import boto3

bedrock_agent = boto3.client("bedrock-agent")

config_path = os.path.join(os.path.dirname(__file__), "..", "..", "kb_config.json")
with open(config_path) as f:
    config = json.load(f)

KB_ID = config["knowledge_base_id"]
BUCKET = os.environ["WORKSHOP_BUCKET"]

print("Creating data source with HIERARCHICAL chunking...")
ds = bedrock_agent.create_data_source(
    knowledgeBaseId=KB_ID,
    name="workshop-hierarchical-chunking",
    dataSourceConfiguration={
        "type": "S3",
        "s3Configuration": {"bucketArn": f"arn:aws:s3:::{BUCKET}"},
    },
    vectorIngestionConfiguration={
        "chunkingConfiguration": {
            "chunkingStrategy": "HIERARCHICAL",
            "hierarchicalChunkingConfiguration": {
                "levelConfigurations": [
                    {"maxTokens": 1500},  # Parent chunks
                    {"maxTokens": 300},   # Child chunks
                ],
                "overlapTokens": 60,
            },
        }
    },
)

ds_id = ds["dataSource"]["dataSourceId"]
print(f"Data source created: {ds_id}")

print("Starting ingestion...")
job = bedrock_agent.start_ingestion_job(knowledgeBaseId=KB_ID, dataSourceId=ds_id)
job_id = job["ingestionJob"]["ingestionJobId"]

while True:
    status = bedrock_agent.get_ingestion_job(
        knowledgeBaseId=KB_ID, dataSourceId=ds_id, ingestionJobId=job_id
    )
    state = status["ingestionJob"]["status"]
    print(f"  Status: {state}")
    if state in ("COMPLETE", "FAILED"):
        break
    time.sleep(5)

config["hierarchical_data_source_id"] = ds_id
with open(config_path, "w") as f:
    json.dump(config, f, indent=2)

print(f"✅ Hierarchical chunking data source ready: {ds_id}")
