# Run vllm
source .venv/bin/activate
CUDA_DEVICE_ORDER=PCI_BUS_ID vllm serve openai/gpt-oss-120b --tool-call-parser openai --reasoning-parser openai_gptoss --enable-auto-tool-choice

# Create venv
uv venv 
source .venv/bin/activate
uv run python -m ensurepip

# Install llama-stack from submodule to our venv
cd llama-stack
pip install --upgrade --editable .
cd ..

# Install llama-stack-client-python from submodule to our venv
cd llama-stack-client-python
pip install --upgrade --editable .
cd ..

# Install other dependencies
pip install litellm sqlalchemy mcp psycopg2-binary

# Run assisted-chat (mostly for postgres?)
export OCM_TOKEN=$(ocm token)
export VLLM_URL=http://nvd-srv-01.nvidia.eng.rdu2.redhat.com:8000/v1
export VLLM_API_TOKEN=foo
make run

# Use llama-stack to query vllm
export OCM_TOKEN=$(ocm token)
export VLLM_URL=http://nvd-srv-01.nvidia.eng.rdu2.redhat.com:8000/v1
export VLLM_API_TOKEN=foo
export GEMINI_API_KEY=""
uv run response_api_test.py


