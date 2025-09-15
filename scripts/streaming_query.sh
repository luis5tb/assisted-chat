#!/bin/bash

set -euo pipefail

# Usage:
#   make streaming_query            # v1 localhost
#   make streaming_query_v2         # v2 localhost
#   API_VERSION=v2 QUERY_ENV=int ./scripts/streaming_query.sh

API_VERSION=${API_VERSION:-v1}   # v1 or v2
QUERY_ENV=${QUERY_ENV:-}         # int|stage|prod|empty=localhost

CYAN='\033[0;36m'
RESET='\033[0m'

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

source "$PROJECT_ROOT/utils/ocm-token.sh"

case "$QUERY_ENV" in
  int)   BASE_URL="https://assisted-chat.api.integration.openshift.com" ;;
  stage) BASE_URL="https://assisted-chat.api.stage.openshift.com" ;;
  prod)  BASE_URL="https://assisted-chat.api.openshift.com" ;;
  *)     BASE_URL="http://localhost:8090" ;;
esac

endpoint_path="/${API_VERSION}/streaming_query"

good_http_response() {
  local status_code="$1"
  [[ "$status_code" -ge 200 && "$status_code" -lt 300 ]]
}

get_models() {
  curl --silent --show-error \
    -H "Authorization: Bearer ${OCM_TOKEN}" \
    "${BASE_URL}/v1/models"
}

select_model() {
  local models_json="$1"
  IFS=$'\t' < <(jq -r '
    .models[] | select(.model_type=="llm")
    | .provider_resource_id as $name
    | .provider_id as $prov
    | "\($name)\t\($prov)"' <<<"$models_json" | fzf --delimiter='\t' --with-nth=1 --accept-nth=1,2 --header="Select model") read -r MODEL PROVIDER
}

echo -e "${CYAN}=== Streaming via ${API_VERSION^^} at ${BASE_URL}${endpoint_path} ===${RESET}"

if ! get_ocm_token; then
  echo "Failed to get OCM token" >&2
  exit 1
fi

MODELS_JSON=$(get_models)
select_model "$MODELS_JSON"
MODEL=${MODEL:-}
PROVIDER=${PROVIDER:-}

read -p "Enter your prompt: " USER_QUERY
USER_QUERY=${USER_QUERY:-Hello from streaming}

payload=$(jq -n --arg q "$USER_QUERY" --arg m "$MODEL" --arg p "$PROVIDER" '{query:$q, model:$m, provider:$p}')

echo -e "${CYAN}--- Streaming (Ctrl+C to stop) ---${RESET}"
curl --no-buffer -N \
  -H "Authorization: Bearer ${OCM_TOKEN}" \
  -H "Accept: text/event-stream" \
  -H "Content-Type: application/json" \
  -X POST "${BASE_URL}${endpoint_path}" \
  --data "$payload"


