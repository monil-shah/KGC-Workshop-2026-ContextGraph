#!/bin/bash
# Clean up all workshop resources.
# Usage: ./cleanup.sh [region]

set -e

REGION="${1:-us-east-1}"
CDK_DIR="$(cd "$(dirname "$0")/../cdk" && pwd)"

echo "🧹 Cleaning up workshop resources..."
echo "   Region: $REGION"
echo ""

# Step 1: Delete Bedrock Knowledge Base (if exists)
KB_CONFIG="$(cd "$(dirname "$0")/../../modules" && pwd)/kb_config.json"
if [ -f "$KB_CONFIG" ]; then
  KB_ID=$(python3 -c "import json; print(json.load(open('$KB_CONFIG')).get('knowledge_base_id', ''))" 2>/dev/null)
  if [ -n "$KB_ID" ]; then
    echo "  Deleting Knowledge Base: $KB_ID"
    aws bedrock-agent delete-knowledge-base \
      --knowledge-base-id "$KB_ID" \
      --region "$REGION" 2>/dev/null || echo "  (already deleted)"
  fi

  GRAPH_ID=$(python3 -c "import json; print(json.load(open('$KB_CONFIG')).get('neptune_graph_id', ''))" 2>/dev/null)
  if [ -n "$GRAPH_ID" ]; then
    echo "  Deleting Neptune Analytics graph: $GRAPH_ID"
    aws neptune-graph delete-graph \
      --graph-identifier "$GRAPH_ID" \
      --skip-snapshot \
      --region "$REGION" 2>/dev/null || echo "  (already deleted)"
  fi

  rm -f "$KB_CONFIG"
fi

# Step 2: Delete custom chunker Lambda
echo "Deleting custom chunker Lambda..."
aws lambda delete-function \
  --function-name workshop-custom-chunker \
  --region "$REGION" 2>/dev/null || echo "  (already deleted)"

# Step 3: CDK destroy
echo "Running cdk destroy..."
cd "$CDK_DIR"
npx cdk destroy --force --region "$REGION"

echo ""
echo "✅ Cleanup complete! All workshop resources have been removed."
