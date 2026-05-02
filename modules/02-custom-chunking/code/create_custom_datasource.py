"""Create a data source with custom Lambda chunking."""
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
LAMBDA_ARN = config["custom_chunker_lambda_arn"]

print("Creating data source with CUSTOM LAMBDA chunking...")
ds = bedrock_agent.create_data_source(
    knowledgeBaseId=KB_ID,
    name="workshop-custom-lambda-chunking",
    dataSourceConfiguration={
        "type": "S3",
        "s3Configuration": {"bucketArn": f"arn:aws:s3:::{BUCKET}"},
    },
    vectorIngestionConfiguration={
        "chunkingConfiguration": {"chunkingStrategy": "NONE"},
        "customTransformationConfiguration": {
            "intermediateStorage": {
                "s3Location": {"uri": f"s3://{BUCKET}/chunking-intermediate/"}
            },
            "transformations": [
                {
                    "stepToApply": "POST_CHUNKING",
                    "transformationFunction": {
                        "transformationLambdaConfiguration": {
                            "lambdaArn": LAMBDA_ARN
                        }
                    },
                }
            ],
        },
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

config["custom_data_source_id"] = ds_id
with open(config_path, "w") as f:
    json.dump(config, f, indent=2)

print(f"✅ Custom Lambda chunking data source ready: {ds_id}")
