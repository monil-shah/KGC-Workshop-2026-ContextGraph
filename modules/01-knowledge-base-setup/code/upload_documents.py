"""Upload sample documents to the workshop S3 bucket."""
import os
import glob
import boto3

s3 = boto3.client("s3")
BUCKET = os.environ["WORKSHOP_BUCKET"]
PREFIX = "documents/"

data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
files = glob.glob(os.path.join(data_dir, "*.md"))

for filepath in files:
    key = PREFIX + os.path.basename(filepath)
    s3.upload_file(filepath, BUCKET, key)
    print(f"Uploaded {os.path.basename(filepath)} → s3://{BUCKET}/{key}")

print(f"\n✅ Uploaded {len(files)} documents to s3://{BUCKET}/{PREFIX}")
