"""
Agent API Test - Test LlamaStack Agent API with MCP Tools

This script tests the LlamaStack Agent API with Model Context Protocol (MCP) tools,
similar to response_api_test.py but using the Agent API instead of the Responses API.

The test performs the same 3-step flow:
1. List existing assisted installer clusters
2. Ask about creating a cluster
3. Provide cluster details for creation

Usage:
    python agent_api_test.py

Requirements:
    - OCM_TOKEN environment variable set
    - assisted-service-mcp container running on port 8000
    - llama-stack configured with a compatible model
"""

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

    print(f"  {len(models) + 1}. Use default model (vllm/openai/gpt-oss-120b)")

    while True:
        try:
            choice = input(f"\n🔢 Select a model (1-{len(models) + 1}): ").strip()

            if not choice:
                print("❌ Please enter a number")
                continue

            choice_num = int(choice)

            if choice_num == len(models) + 1:
                # Use default model
                default_model = "vllm/openai/gpt-oss-120b"
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


async def create_agent_with_mcp_tools(client, model_id):
    """Create an agent with MCP tools configuration using Agent wrapper like lightspeed-stack."""
    print(f"🤖 Creating agent with MCP tools using model: {model_id}")
    
    try:
        # First, register the MCP toolgroup if not already registered
        await register_mcp_toolgroup(client)
        
        # Create agent using AsyncAgent (like lightspeed-stack)
        from llama_stack_client.lib.agents.agent import AsyncAgent
        import json
        
        ocm_token = os.getenv("OCM_TOKEN")
        
        # Create agent first (like lightspeed-stack does)
        agent = AsyncAgent(
            client,
            model=model_id,
            instructions=(
                "You are a helpful assistant with access to tools for managing OpenShift clusters. "
                "When answering questions about clusters, resources, or infrastructure, "
                "use the available tools to query the actual system state rather than "
                "providing generic responses. Always use tools when asked about cluster information."
            ),
            tools=["assisted"],  # MCP toolgroup name
            max_infer_iters=10,
            sampling_params={
                "strategy": {"type": "top_p", "temperature": 0.7, "top_p": 0.95},
                "max_tokens": 2048,
            }
        )
        
        # Initialize the agent (like lightspeed-stack does)
        await agent.initialize()
        
        # Set MCP headers on the agent (like lightspeed-stack does)
        if ocm_token:
            mcp_headers = {
                "http://0.0.0.0:8000/mcp": {
                    "Authorization": f"Bearer {ocm_token}"
                }
            }
            
            agent.extra_headers = {
                "X-LlamaStack-Provider-Data": json.dumps({
                    "mcp_headers": mcp_headers
                })
            }
        
        print("🎯 Agent Created Successfully:")
        print(f"  Agent ID: {agent.agent_id}")
        print(f"  MCP Headers: {'Set' if ocm_token else 'None'}")
        print()
        
        return agent

    except Exception as e:
        print(f"❌ Error creating agent: {e}")
        return None


async def register_mcp_toolgroup(client):
    """Register the MCP toolgroup if not already registered."""
    print("🔧 Registering MCP toolgroup...")
    
    try:
        # Check if toolgroup is already registered
        registered_toolgroups = await client.toolgroups.list()
        registered_names = [tg.provider_resource_id for tg in registered_toolgroups]
        
        if "assisted" not in registered_names:
            print("  📝 Registering 'assisted' MCP toolgroup...")
            await client.toolgroups.register(
                toolgroup_id="assisted",
                provider_id="model-context-protocol",
                mcp_endpoint={"uri": "http://0.0.0.0:8000/mcp"}
            )
            print("  ✅ MCP toolgroup registered successfully")
        else:
            print("  ✅ MCP toolgroup already registered")
            
    except Exception as e:
        print(f"  ⚠️  Warning: Could not register MCP toolgroup: {e}")
        print("  💡 Make sure the MCP server is running and accessible")


async def create_agent_session(agent, session_name="MCP Test Session"):
    """Create a new session for the agent."""
    print(f"📝 Creating agent session: {session_name}")
    
    try:
        session_id = await agent.create_session(session_name=session_name)
        
        print("✅ Agent Session Created:")
        print(f"  Session ID: {session_id}")
        print()
        
        return session_id

    except Exception as e:
        print(f"❌ Error creating agent session: {e}")
        return None


async def test_agent_turn(agent, session_id, query, turn_number=1):
    """Test agent turn with MCP tools using non-streaming response like lightspeed-stack."""
    print(f"🔧 Testing agent turn #{turn_number} with query: {query}")
    
    try:
        # Create a turn with the agent using the Agent wrapper (like lightspeed-stack)
        # The MCP headers are already set on the agent.extra_headers
        response = await agent.create_turn(
            messages=[{"role": "user", "content": query}],
            session_id=session_id,
            stream=False,  # Use non-streaming like lightspeed-stack
            toolgroups=["assisted"]  # Explicitly specify the MCP toolgroup
        )

        # Process non-streaming response (like lightspeed-stack)
        print(f"🛠️  Agent Turn #{turn_number} Response:")
        print(f"  Turn ID: {response.turn_id}")
        print(f"  Input Messages: {len(response.input_messages)}")
        print(f"  Steps: {len(response.steps) if response.steps else 0}")
        
        # Display steps (tool calls, inference, etc.)
        if response.steps:
            for i, step in enumerate(response.steps):
                step_type = step.step_type
                print(f"  Step {i+1}: {step_type}")
                
                # Handle tool execution steps
                if step_type == "tool_execution" and hasattr(step, 'tool_calls'):
                    for j, tool_call in enumerate(step.tool_calls):
                        print(f"    🔧 Tool Call {j+1}: {tool_call.tool_name}")
                        if hasattr(tool_call, 'arguments'):
                            print(f"      Arguments: {tool_call.arguments}")
                    
                    if hasattr(step, 'tool_responses'):
                        for j, tool_response in enumerate(step.tool_responses):
                            print(f"    ✅ Tool Response {j+1}:")
                            if hasattr(tool_response, 'content'):
                                for content_item in tool_response.content:
                                    if hasattr(content_item, 'text'):
                                        content_preview = content_item.text[:200]
                                        print(f"      Result: {content_preview}...")
                
                # Handle inference steps
                elif step_type == "inference" and hasattr(step, 'api_model_response'):
                    model_response = step.api_model_response
                    if hasattr(model_response, 'content'):
                        content_preview = model_response.content[:200]
                        print(f"    💬 Model Response: {content_preview}...")

        # Display final output message
        if hasattr(response, 'output_message') and response.output_message:
            if hasattr(response.output_message, 'content'):
                content = response.output_message.content
                print(f"  🎯 Final Response: {content[:300]}...")
        
        print()
        return response

    except Exception as e:
        print(f"❌ Error with agent turn: {e}")
        return None


async def main():
    """Main function - test agent API with MCP tools."""
    print("🚀 Agent API Test - Direct llama-stack Access")
    print("=" * 55)

    # Configuration file path (same as lightspeed-stack uses)
    config_path = "config/llama_stack_client_config.yaml"

    if not Path(config_path).exists():
        print(f"❌ Config file not found: {config_path}")
        print("💡 Make sure you run this from the assisted-chat root directory")
        print("💡 The config file should be at: config/llama_stack_client_config.yaml")
        sys.exit(1)

    print(f"📁 Using config: {config_path}")

    # Check for required environment variables
    required_env_vars = ["GEMINI_API_KEY", "OCM_TOKEN"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]

    if missing_vars:
        print(f"⚠️  Warning: Missing environment variables: {', '.join(missing_vars)}")
        print("💡 Some providers/tools may not work without proper API keys")

    try:
        # Initialize the llama-stack client
        print("\n🔄 Initializing llama-stack client...")
        print("   This is exactly how lightspeed-stack initializes the client")

        client = AsyncLlamaStackAsLibraryClient(config_path)
        await client.initialize()

        print("✅ Client initialized successfully!")
        print("   llama-stack is now ready to use\n")

        # List available models
        models = await list_available_models(client)

        if not models:
            print("❌ No models available - check your configuration")
            return

        print("\n✅ Model listing completed successfully!")

        # Let user select a model from the available models
        test_model = select_model_from_list(models)

        if not test_model:
            print("❌ No model selected - exiting")
            return

        print(f"\n🎯 Using model '{test_model}' for testing...\n")

        # Test inference API (optional)
        # await test_inference_api(client, test_model)

        # Create agent with MCP tools
        agent = await create_agent_with_mcp_tools(client, test_model)
        if not agent:
            print("❌ Failed to create agent - exiting")
            return

        # Create agent session
        session_id = await create_agent_session(agent)
        if not session_id:
            print("❌ Failed to create agent session - exiting")
            return

        # Test with MCP tools using the same 3 queries as response_api_test.py
        print("🤔 Testing Agent API with chained queries (requires assisted-service-mcp container to be running)")
        
        try:
            # First query: Get existing clusters
            print("\n" + "="*60)
            print("🔍 QUERY 1: Getting existing clusters")
            print("="*60)
            turn_1 = await test_agent_turn(
                agent,
                session_id,
                "What assisted installer clusters do I have? Please use tools to get real data.",
                1
            )

            # Second query: Ask about creating a cluster (same session continues the conversation)
            print("\n" + "="*60)
            print("🏗️  QUERY 2: Asking about cluster creation")
            print("="*60)
            turn_2 = await test_agent_turn(
                agent,
                session_id,
                "can you create a cluster",
                2
            )

            # Third query: Provide cluster details (same session continues the conversation)
            print("\n" + "="*60)
            print("📋 QUERY 3: Providing cluster details")
            print("="*60)
            turn_3 = await test_agent_turn(
                agent,
                session_id,
                "luis-test, 4.19.10, example.com, SNO, no ssh-key",
                3
            )

            print("\n✅ All agent turns completed successfully!")
            print(f"   Agent ID: {agent.agent_id}")
            print(f"   Session ID: {session_id}")
            
            # Extract turn IDs from responses
            turn_ids = []
            for turn in [turn_1, turn_2, turn_3]:
                if turn and hasattr(turn, 'turn_id'):
                    turn_ids.append(turn.turn_id)
                else:
                    turn_ids.append('N/A')
            
            if any(tid != 'N/A' for tid in turn_ids):
                print(f"   Turn IDs: {' -> '.join(turn_ids)}")

        except Exception as e:
            print(f"⚠️  Agent tools test failed (expected if MCP server not accessible): {e}")

        print("\n🎉 All tests completed successfully!")

    except Exception as e:
        print(f"❌ Error initializing client: {e}")
        print("\n🔍 Troubleshooting:")
        print("   1. Ensure you're in the assisted-chat root directory")
        print("   2. Check that config/llama_stack_client_config.yaml exists")
        print("   3. Verify environment variables are set:")
        print("      export GEMINI_API_KEY='your-api-key'")
        print("      export OCM_TOKEN='your-ocm-token'")
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
