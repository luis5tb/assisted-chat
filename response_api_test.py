import asyncio
import os
import sys
import time
from pathlib import Path
from llama_stack import AsyncLlamaStackAsLibraryClient


async def list_available_models(client):
    """List all available models with detailed information."""
    print("🔍 Listing available models...")
    try:
        models = await client.models.list()
        print(f"📋 Found {len(models)} models:\n")
        
        if not models:
            print("❌ No models are configured!")
            print("💡 Check your config/llama_stack_client_config.yaml file")
            return []
        
        for i, model in enumerate(models, 1):
            print(f"  {i:2d}. 📦 {model.identifier}")
            print(f"       Provider: {model.provider_id}")
            print(f"       Type: {model.model_type}")
            
            # Show additional details if available
            if hasattr(model, 'provider_model_id') and model.provider_model_id != model.model_id:
                print(f"       Provider Model: {model.provider_model_id}")
            
            if hasattr(model, 'metadata') and model.metadata:
                print(f"       Metadata: {model.metadata}")
            print()
            
        return models
    except Exception as e:
        print(f"❌ Error listing models: {e}")
        return []


async def test_inference_api(client, model_id):
    """Test the inference API directly."""
    print(f"🧠 Testing inference API with model: {model_id}")
    try:
        response = await client.inference.chat_completion(
            model_id=model_id,
            messages=[
                {"role": "user", "content": "What is Kubernetes? Give a brief answer."}
            ]
        )
        
        print("💬 Inference API Response:")
        print(f"  Content: {response.completion_message.content}")
        print(f"  Stop Reason: {response.completion_message.stop_reason}")
        print()
        
    except Exception as e:
        print(f"❌ Error with inference API: {e}")


async def test_responses_api(client, model_id):
    """Test the responses API (what lightspeed-stack uses)."""
    print(f"🤖 Testing responses API with model: {model_id}")
    try:
        response = await client.responses.create(
            input="List 3 benefits of using containers in software development.",
            model=model_id,
            instructions="You are a helpful technical assistant. Provide clear, concise answers.",
            store=True
        )
        
        print("🎯 Responses API Response:")
        print(f"  Response ID: {response.id}")
        print(f"  Status: {response.status}")
        print(f"  Output items: {len(response.output)}")
        
        for i, output_item in enumerate(response.output):
            print(f"  Output {i}:")
            if hasattr(output_item, 'content') and output_item.content:
                if isinstance(output_item.content, list):
                    for content_item in output_item.content:
                        if hasattr(content_item, 'text'):
                            print(f"    Text: {content_item.text[:200]}...")
                elif hasattr(output_item.content, 'text'):
                    print(f"    Text: {output_item.content.text[:200]}...")
                elif isinstance(output_item.content, str):
                    print(f"    Text: {output_item.content[:200]}...")
        print()
        
    except Exception as e:
        print(f"❌ Error with responses API: {e}")


async def test_mcp_tools(client, model_id):
    """Test responses API with MCP tools (similar to lightspeed-stack)."""
    print(f"🔧 Testing responses API with MCP tools using model: {model_id}")
    ocm_token = os.getenv("OCM_TOKEN")

    try:
        # This should trigger the MCP tools that are configure
        """
        curl -X POST http://localhost:8090/v1/query -H "Content-Type: application/json" -H "Authorization: Bearer ${OCM_TOKEN}" -d '{
            "query": "What assisted installer clusters do I have? Please use tools to get real data.",
            "model": "openai/gpt-oss-20b",
            "provider": "vllm"
        }'
        """
        response = await client.responses.create(
            input="What assisted installer clusters do I have? Please use tools to get real data.",
            model=model_id,
            instructions=(
                "You are a helpful assistant with access to tools. "
                "When answering questions about clusters, resources, or infrastructure, "
                "use the available tools to query the actual system state rather than "
                "providing generic responses."
            ),
            tools=[
                {
                    "type": "mcp",
                    "server_label": "assisted",
                    "server_url": "http://0.0.0.0:8000/mcp",
                    "require_approval": "never",
                    #"authorization": ocm_token    # not yet supported by llama-stack
                    "headers": {
                        "Authorization": f"Bearer {ocm_token}"
                    }
                }
            ],
            store=True
        )
        
        print("🛠️  MCP Tools Response:")
        print(f"  Response ID: {response.id}")
        print(f"  Status: {response.status}")
        print(f"  Output items: {len(response.output)}")
        
        
        
        for i, output_item in enumerate(response.output):
            print(f"  Output {i}: {type(output_item).__name__}")
            
            # Check for tool calls
            if hasattr(output_item, 'tool_calls') and output_item.tool_calls:
                print(f"    🔨 Found {len(output_item.tool_calls)} tool calls:")
                for j, tool_call in enumerate(output_item.tool_calls):
                    tool_name = getattr(tool_call.function, 'name', 'unknown') if hasattr(tool_call, 'function') else 'unknown'
                    print(f"      Tool {j}: {tool_name}")
            
            # Check for content
            if hasattr(output_item, 'content') and output_item.content:
                #content_preview = str(output_item.content) + "..." if len(str(output_item.content)) > 150 else str(output_item.content)
                content_preview = str(output_item.content)
                print(f"    💬 Content: {content_preview}")
                
        print()
        
    except Exception as e:
        print(f"❌ Error with MCP tools: {e}")


async def main():
    """Main function - mimics how lightspeed-stack initializes llama-stack."""
    print("🚀 Response API Test - Direct llama-stack Access")
    print("=" * 55)
    
    # Configuration file path (same as lightspeed-stack uses)
    config_path = "config/llama_stack_client_config.yaml"
    
    if not Path(config_path).exists():
        print(f"❌ Config file not found: {config_path}")
        print("💡 Make sure you run this from the assisted-chat root directory")
        print("💡 The config file should be at: config/llama_stack_client_config.yaml")
        sys.exit(1)
    
    print(f"📁 Using config: {config_path}")
    
    # Check for required environment variables (same ones lightspeed-stack uses)
    required_env_vars = ["GEMINI_API_KEY"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"⚠️  Warning: Missing environment variables: {', '.join(missing_vars)}")
        print("💡 Some providers may not work without proper API keys")
    
    try:
        # Initialize the llama-stack client (same as lightspeed-stack does)
        print("\n🔄 Initializing llama-stack client...")
        print("   This is exactly how lightspeed-stack initializes the client")
        
        client = AsyncLlamaStackAsLibraryClient(config_path)
        await client.initialize()
        
        print("✅ Client initialized successfully!")
        print("   llama-stack is now ready to use\n")
        

        
        ## List available models (primary functionality)
        models = await list_available_models(client)
        
        if not models:
            print("❌ No models available - check your configuration")
            return

        print("\n✅ Model listing completed successfully!")
        
        # Use the GPT_OSS Model
        # Running it with VLLM with the next:
        # https://github.com/vllm-project/vllm/pull/22386
        #  CUDA_DEVICE_ORDER=PCI_BUS_ID vllm serve openai/gpt-oss-20b --tool-call-parser openai --reasoning-parser openai_gptoss --enable-auto-tool-choice 
        test_model = "vllm/openai/gpt-oss-20b"
        #test_model = "Qwen/Qwen3-8B"
        #test_model = "gemini/gemini-2.0-flash"
        print(f"🎯 Using model '{test_model}' for testing...\n")
        
        # Test inference API
        #await test_inference_api(client, test_model)
        
        # Test responses API (what lightspeed-stack uses)
        #await test_responses_api(client, test_model)


        # Test with MCP tools (if you want to test tool integration)
        # Note: This will only work if the MCP server is running
        #print("🤔 Want to test MCP tools? (This requires the assisted-service-mcp container to be running)")
        try:
            await test_mcp_tools(client, test_model)
        except Exception as e:
            print(f"⚠️  MCP tools test failed (expected if MCP server not accessible): {e}")

        time.sleep(20)

        
    except Exception as e:
        print(f"❌ Error initializing client: {e}")
        print("\n🔍 Troubleshooting:")
        print("   1. Ensure you're in the assisted-chat root directory")
        print("   2. Check that config/llama_stack_client_config.yaml exists")
        print("   3. Verify environment variables are set:")
        print("      export GEMINI_API_KEY='your-api-key'")
        print("   4. Make sure llama-stack dependencies are installed:")
        print("      uv add llama-stack")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())