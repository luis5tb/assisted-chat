import asyncio
import os
import sys
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


def select_model_from_list(models):
    """Allow user to select a model from the available models list."""
    if not models:
        return None

    print("\n🎯 Model Selection")
    print("=" * 40)

    # Show models with numbers for selection
    for i, model in enumerate(models, 1):
        print(f"  {i}. {model.identifier} ({model.provider_id})")

    print(f"  {len(models) + 1}. Use default model (vllm/openai/gpt-oss-20b)")

    while True:
        try:
            choice = input(f"\n🔢 Select a model (1-{len(models) + 1}): ").strip()

            if not choice:
                print("❌ Please enter a number")
                continue

            choice_num = int(choice)

            if choice_num == len(models) + 1:
                # Use default model
                default_model = "vllm/openai/gpt-oss-20b"
                print(f"✅ Using default model: {default_model}")
                return default_model
            elif 1 <= choice_num <= len(models):
                selected_model = models[choice_num - 1]
                print(f"✅ Selected model: {selected_model.identifier}")
                return selected_model.identifier
            else:
                print(f"❌ Please enter a number between 1 and {len(models) + 1}")

        except ValueError:
            print("❌ Please enter a valid number")
        except KeyboardInterrupt:
            print("\n\n👋 Exiting...")
            sys.exit(0)


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


async def test_mcp_tools(client, model_id, input_query, response_id=None):
    """Test responses API with MCP tools (similar to lightspeed-stack)."""
    print(f"🔧 Testing responses API with MCP tools using model: {model_id}")
    print(f"📝 Query: {input_query}")
    if response_id:
        print(f"🔗 Using response ID: {response_id}")
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
        # Prepare the request parameters
        request_params = {
            "input": input_query,
            "model": model_id,
            "instructions": (
                "You are a helpful assistant with access to tools. "
                "When answering questions about clusters, resources, or infrastructure, "
                "use the available tools to query the actual system state rather than "
                "providing generic responses."
            ),
            "tools": [
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
            "store": True
        }

        # Add response_id if provided for chaining
        if response_id:
            request_params["previous_response_id"] = response_id

        response = await client.responses.create(**request_params)

        print("🛠️  MCP Tools Response:")
        print(f"  Response ID: {response.id}")
        print(f"  Status: {response.status}")
        print(f"  Output items: {len(response.output)}")



        for i, output_item in enumerate(response.output):
            output_type = type(output_item).__name__
            print(f"  Output {i}: {output_type}")

            # Handle MCP tool calls (OutputOpenAIResponseOutputMessageMcpCall)
            if "McpCall" in output_type:
                print("    🔧 MCP Tool Call:")
                if hasattr(output_item, 'id'):
                    print(f"      ID: {output_item.id}")
                if hasattr(output_item, 'name'):
                    print(f"      Tool Name: {output_item.name}")
                if hasattr(output_item, 'server_label'):
                    print(f"      Server Label: {output_item.server_label}")
                if hasattr(output_item, 'arguments'):
                    print(f"      Arguments: {output_item.arguments}")
                if hasattr(output_item, 'output') and output_item.output:
                    print(f"      🔍 Tool Output: {output_item.output}")
                if hasattr(output_item, 'error') and output_item.error:
                    print(f"      ❌ Tool Error: {output_item.error}")

            # Handle MCP list tools (OutputOpenAIResponseOutputMessageMcpListTools)
            elif "McpListTools" in output_type:
                print("    📋 MCP List Tools:")
                if hasattr(output_item, 'server_label'):
                    print(f"      Server Label: {output_item.server_label}")
                if hasattr(output_item, 'tools') and output_item.tools:
                    print(f"      Available Tools: {len(output_item.tools)}")
                    for j, tool in enumerate(output_item.tools):
                        tool_name = getattr(tool, 'name', 'unknown') if hasattr(tool, 'name') else 'unknown'
                        print(f"        {j+1}. {tool_name}")

            # Handle regular message content
            elif hasattr(output_item, 'content') and output_item.content:
                content_preview = str(output_item.content)
                print(f"    💬 Content: {content_preview}")

        print()

        # Return the response ID for chaining
        return response.id

    except Exception as e:
        import traceback
        print(f"❌ Error with MCP tools: {e}")
        print(f"\n🔍 Full traceback:")
        traceback.print_exc()
        return None


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
    required_env_vars = ["GEMINI_API_KEY", "OCM_TOKEN"]
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

        # Let user select a model from the available models
        # Running it with VLLM with the next:
        # https://github.com/vllm-project/vllm/pull/22386
        #  CUDA_DEVICE_ORDER=PCI_BUS_ID vllm serve openai/gpt-oss-20b --tool-call-parser openai --reasoning-parser openai_gptoss --enable-auto-tool-choice
        test_model = select_model_from_list(models)

        if not test_model:
            print("❌ No model selected - exiting")
            return

        print(f"\n🎯 Using model '{test_model}' for testing...\n")

        # Test inference API
        # await test_inference_api(client, test_model)

        # Test responses API (what lightspeed-stack uses)
        #await test_responses_api(client, test_model)


        # Test with MCP tools (if you want to test tool integration)
        # Note: This will only work if the MCP server is running
        print("🤔 Testing MCP tools with chained queries (requires assisted-service-mcp container to be running)")
        try:
            # First query: Get existing clusters
            print("\n" + "="*60)
            print("🔍 QUERY 1: Getting existing clusters")
            print("="*60)
            response_id_1 = await test_mcp_tools(
                client,
                test_model,
                "What assisted installer clusters do I have? Please use tools to get real data."
            )

            # Second query: Ask about creating a cluster (chained with first response)
            # Small delay to allow async queue to process the first response
            print("\n⏳ Waiting for responses store to process...")
            await asyncio.sleep(1.0)

            print("\n" + "="*60)
            print("🏗️  QUERY 2: Asking about cluster creation")
            print("="*60)
            response_id_2 = await test_mcp_tools(
                client,
                test_model,
                "can you create a cluster",
                response_id_1
            )

            # Third query: Provide cluster details (chained with second response)
            # Small delay to allow async queue to process the second response
            print("\n⏳ Waiting for responses store to process...")
            await asyncio.sleep(1.0)

            print("\n" + "="*60)
            print("📋 QUERY 3: Providing cluster details")
            print("="*60)
            response_id_3 = await test_mcp_tools(
                client,
                test_model,
                "luis-test, 4.19.10, example.com, SNO, no ssh-key",
                response_id_2
            )

            print("\n✅ All chained queries completed successfully!")
            print(f"   Response IDs: {response_id_1} -> {response_id_2} -> {response_id_3}")

        except Exception as e:
            print(f"⚠️  MCP tools test failed (expected if MCP server not accessible): {e}")

        print("\n🎉 All tests completed successfully!")

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
    finally:
        # Properly cleanup the client to avoid background task cancellation errors
        try:
            if 'client' in locals():
                print("\n🧹 Cleaning up client...")
                # Try to close the client properly if it has a close method
                if hasattr(client, 'close'):
                    await client.close()
                elif hasattr(client, 'aclose'):
                    await client.aclose()
                # Give any remaining tasks a moment to finish
                await asyncio.sleep(0.1)
        except Exception as cleanup_error:
            print(f"⚠️  Warning during cleanup: {cleanup_error}")

        print("👋 Script finished!")


if __name__ == "__main__":
    asyncio.run(main())
