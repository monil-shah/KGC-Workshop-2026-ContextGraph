import json
import os
import urllib3
import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest


def handler(event, context):
    request_type = event.get("RequestType", "")
    if request_type == "Delete":
        return {"Status": "SUCCESS"}

    endpoint = os.environ["COLLECTION_ENDPOINT"]
    index_name = os.environ["INDEX_NAME"]
    url = f"https://{endpoint}/{index_name}"

    body = json.dumps({
        "settings": {
            "index.knn": True,
            "number_of_shards": 2,
            "number_of_replicas": 0,
        },
        "mappings": {
            "properties": {
                "embedding": {
                    "type": "knn_vector",
                    "dimension": 1024,
                    "method": {
                        "engine": "faiss",
                        "name": "hnsw",
                        "space_type": "l2",
                    },
                },
                "text": {"type": "text"},
                "metadata": {"type": "text"},
            }
        },
    })

    session = boto3.Session()
    credentials = session.get_credentials().get_frozen_credentials()
    request = AWSRequest(
        method="PUT", url=url, data=body,
        headers={"Content-Type": "application/json"},
    )
    SigV4Auth(credentials, "aoss", session.region_name).add_auth(request)

    http = urllib3.PoolManager()
    response = http.request("PUT", url, body=body, headers=dict(request.headers))
    print(f"Index creation response: {response.status} {response.data.decode()}")

    return {"Status": "SUCCESS"}
