"""Deploy the custom chunking Lambda function."""
import os
import json
import zipfile
import tempfile
import boto3

lambda_client = boto3.client("lambda")
LAMBDA_ROLE_ARN = os.environ["LAMBDA_ROLE_ARN"]
FUNCTION_NAME = "workshop-custom-chunker"

# Lambda function code
lambda_code = '''
import json
import re
import boto3

s3 = boto3.client("s3")


def parse_s3_uri(uri):
    """Parse s3://bucket/key into (bucket, key)."""
    parts = uri.replace("s3://", "").split("/", 1)
    return parts[0], parts[1]


def chunk_by_markdown_headers(text, source_uri=""):
    """Split on namespace/metric boundaries, preserving structure and adding metadata."""
    sections = re.split(r"\\n(?=##+ )", text)
    chunks = []
    current_namespace = "unknown"

    for section in sections:
        section = section.strip()
        if not section or len(section) < 20:
            continue

        header_match = re.match(r"^(#+)\\s+(.+)", section)
        title = header_match.group(2) if header_match else "Introduction"
        level = len(header_match.group(1)) if header_match else 1

        # Track namespace context
        ns_match = re.search(r"Namespace:\\s*(\\w+)", section)
        if ns_match:
            current_namespace = ns_match.group(1)

        # Detect metric definitions
        metric_match = re.search(r"Metric:\\s*(\\w+)", title)
        metric_name = metric_match.group(1) if metric_match else ""

        # Detect doc type
        doc_type = "general"
        if metric_name:
            doc_type = "metric_definition"
        elif "Reconciliation" in title or "Matching" in title:
            doc_type = "reconciliation_rule"
        elif "GRC" in section or "SOX" in section or "Compliance" in title:
            doc_type = "compliance_policy"
        elif "DEC-" in section or "Decision" in title:
            doc_type = "decision_record"

        chunks.append({
            "content": section,
            "metadata": {
                "section_title": title,
                "namespace": current_namespace,
                "metric_name": metric_name,
                "doc_type": doc_type,
                "source_document": source_uri,
                "has_json": str("```json" in section or "```" in section).lower(),
                "chunk_strategy": "namespace_aware",
            },
        })

    return chunks


def handler(event, context):
    """Process documents from Bedrock KB ingestion pipeline."""
    input_files = event.get("inputFiles", [])
    output_files = []

    for input_file in input_files:
        content_batches = input_file.get("contentBatches", [])

        for batch in content_batches:
            input_key = batch["key"]
            bucket, key = parse_s3_uri(input_key)

            # Read the parsed content from S3
            response = s3.get_object(Bucket=bucket, Key=key)
            content = json.loads(response["Body"].read().decode("utf-8"))

            all_chunks = []
            for file_content in content.get("fileContents", [content]):
                text = file_content.get("contentBody", file_content.get("content", ""))
                source = file_content.get("sourceUri", input_key)
                chunks = chunk_by_markdown_headers(text, source)
                all_chunks.extend(chunks)

            # Write chunked output back to S3
            output_key = key.replace(".json", "-chunked.json")
            output_body = {
                "fileContents": [
                    {
                        "contentBody": chunk["content"],
                        "contentType": "TEXT",
                        "contentMetadata": chunk["metadata"],
                    }
                    for chunk in all_chunks
                ]
            }

            s3.put_object(
                Bucket=bucket,
                Key=output_key,
                Body=json.dumps(output_body),
                ContentType="application/json",
            )

            output_files.append({"key": f"s3://{bucket}/{output_key}"})

    return {"outputFiles": output_files}
'''

# Package and deploy
print("Packaging Lambda function...")
with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
    with zipfile.ZipFile(tmp, "w") as zf:
        zf.writestr("lambda_function.py", lambda_code)
    tmp_path = tmp.name

with open(tmp_path, "rb") as f:
    zip_bytes = f.read()
os.unlink(tmp_path)

try:
    lambda_client.get_function(FunctionName=FUNCTION_NAME)
    print("Updating existing Lambda function...")
    lambda_client.update_function_code(
        FunctionName=FUNCTION_NAME, ZipFile=zip_bytes
    )
except lambda_client.exceptions.ResourceNotFoundException:
    print("Creating Lambda function...")
    lambda_client.create_function(
        FunctionName=FUNCTION_NAME,
        Runtime="python3.12",
        Role=LAMBDA_ROLE_ARN,
        Handler="lambda_function.handler",
        Code={"ZipFile": zip_bytes},
        Timeout=300,
        MemorySize=256,
    )

print(f"✅ Lambda function deployed: {FUNCTION_NAME}")

# Save Lambda ARN
func = lambda_client.get_function(FunctionName=FUNCTION_NAME)
config_path = os.path.join(os.path.dirname(__file__), "..", "..", "kb_config.json")
with open(config_path) as f:
    config = json.load(f)
config["custom_chunker_lambda_arn"] = func["Configuration"]["FunctionArn"]
with open(config_path, "w") as f:
    json.dump(config, f, indent=2)
