#!/bin/bash

set -o nounset
set -o errexit
set -o pipefail

: "${UNIQUE_ID:?UNIQUE_ID is required}"
OCM_TOKEN=$(curl -sSf -X POST https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=$CLIENT_ID" \
  -d "client_secret=$CLIENT_SECRET" | jq -r '.access_token')
export OCM_TOKEN

WORK_DIR=$(pwd)
TEST_DIR="${WORK_DIR}/test/evals"
TEMP_DIR=$(mktemp -d)

cd $TEMP_DIR

echo "$OCM_TOKEN" > ocm_token.txt
echo "GEMINI_API_KEY=${GEMINI_API_KEY}" > .env

cp $TEST_DIR/eval_data.yaml $TEMP_DIR/eval_data.yaml
sed -i "s/uniq-cluster-name/${UNIQUE_ID}/g" $TEMP_DIR/eval_data.yaml
sed -i "s|: ../scripts|: ${WORK_DIR}/test/scripts|g" $TEMP_DIR/eval_data.yaml

python $TEST_DIR/eval.py --agent_endpoint "${AGENT_URL}:${AGENT_PORT}" --agent_auth_token_file $TEMP_DIR/ocm_token.txt --eval_data_yaml $TEMP_DIR/eval_data.yaml
