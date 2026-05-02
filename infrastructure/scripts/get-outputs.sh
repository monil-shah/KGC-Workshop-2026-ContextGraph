#!/bin/bash
# Fetch CDK stack outputs and export as environment variables.
# Usage: source get-outputs.sh [stack-name] [region]

STACK_NAME="${1:-AgenticRagWorkshopStack}"
REGION="${2:-us-east-1}"

echo "Fetching outputs from stack: $STACK_NAME in $REGION..."

OUTPUTS=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query 'Stacks[0].Outputs' \
  --output json 2>/dev/null)

if [ $? -ne 0 ]; then
  echo "❌ Failed to fetch stack outputs. Is the stack deployed?"
  return 1 2>/dev/null || exit 1
fi

get_output() {
  echo "$OUTPUTS" | python3 -c "
import json, sys
for o in json.load(sys.stdin):
    if o['OutputKey'] == '$1': print(o['OutputValue'])
"
}

export WORKSHOP_BUCKET=$(get_output WorkshopBucket)
export OPENSEARCH_COLLECTION_ARN=$(get_output OpenSearchCollectionArn)
export KB_ROLE_ARN=$(get_output KnowledgeBaseRoleArn)
export LAMBDA_ROLE_ARN=$(get_output LambdaRoleArn)
export AWS_DEFAULT_REGION="$REGION"

echo "✅ Environment variables set:"
echo "   WORKSHOP_BUCKET=$WORKSHOP_BUCKET"
echo "   OPENSEARCH_COLLECTION_ARN=$OPENSEARCH_COLLECTION_ARN"
echo "   KB_ROLE_ARN=$KB_ROLE_ARN"
echo "   LAMBDA_ROLE_ARN=$LAMBDA_ROLE_ARN"
echo "   AWS_DEFAULT_REGION=$AWS_DEFAULT_REGION"
