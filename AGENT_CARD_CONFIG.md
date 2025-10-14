# Agent Card Configuration

This document explains how to configure the A2A Agent Card for the Lightspeed service using a YAML configuration file.

## Overview

The A2A Agent Card defines the capabilities, skills, and metadata of the Lightspeed AI assistant according to the Agent-to-Agent (A2A) protocol. Previously, this was hardcoded in the application. Now, it can be configured via a YAML file for flexibility and easier customization.

## Configuration

### 1. Enable Agent Card Configuration

In your `lightspeed-stack.yaml` configuration file, add the `agent_card_path` field under the `customization` section:

```yaml
customization:
  system_prompt_path: "/tmp/systemprompt.txt"
  agent_card_path: "/tmp/agentcard.yaml"  # Path to your agent card YAML file
  disable_query_system_prompt: false
```

### 2. Create Agent Card YAML File

Create a YAML file with the following structure (see `config/agentcard.yaml` for a complete example):

```yaml
# Basic agent information
name: "OpenShift Assisted Installer AI Assistant"
description: "AI-powered assistant specialized in OpenShift cluster installation"

# Provider information
provider:
  organization: "Red Hat"
  url: "https://redhat.com"

# Agent capabilities
capabilities:
  streaming: true
  pushNotifications: false
  stateTransitionHistory: false

# Default input and output modes
defaultInputModes:
  - "text/plain"

defaultOutputModes:
  - "text/plain"

# Agent skills - define what the agent can do
skills:
  - id: "cluster_installation_guidance"
    name: "Cluster Installation Guidance"
    description: "Provide guidance and assistance for OpenShift cluster installation"
    tags:
      - "openshift"
      - "installation"
    inputModes:
      - "text/plain"
      - "application/json"
    outputModes:
      - "text/plain"
      - "application/json"
    examples:
      - "How do I install OpenShift using assisted-installer?"
      - "What are the prerequisites for OpenShift installation?"

# Security configuration
security:
  - bearer: []

security_schemes:
  bearer:
    type: "http"
    scheme: "bearer"
    bearer_format: "JWT"
    description: "Bearer token for authentication"
```

## Agent Card Structure

### Required Fields

- **name**: The name of the agent
- **description**: A description of the agent's purpose and capabilities
- **provider**: Organization information
  - **organization**: Organization name
  - **url**: Organization URL

### Optional Fields

- **capabilities**: Agent capabilities
  - **streaming**: Whether the agent supports streaming responses (default: true)
  - **pushNotifications**: Whether push notifications are supported (default: false)
  - **stateTransitionHistory**: Whether state transition history is available (default: false)

- **defaultInputModes**: Array of supported input MIME types (default: ["text/plain"])
- **defaultOutputModes**: Array of supported output MIME types (default: ["text/plain"])

- **skills**: Array of agent skills. Each skill has:
  - **id**: Unique identifier for the skill
  - **name**: Human-readable name
  - **description**: What the skill does
  - **tags**: Array of tags for categorization
  - **inputModes**: Supported input MIME types for this skill
  - **outputModes**: Supported output MIME types for this skill
  - **examples**: Example queries that use this skill

- **security**: Security configuration (default: bearer token)
- **security_schemes**: Security scheme definitions

## Fallback Behavior

If no `agent_card_path` is specified in the configuration, the application will use the default hardcoded agent card with predefined skills for OpenShift cluster installation.

## Example Use Cases

### 1. Custom Skills for Different Domains

You can create specialized agent cards for different use cases:

```yaml
# For development environment
skills:
  - id: "dev_cluster_setup"
    name: "Development Cluster Setup"
    description: "Quick setup for development clusters"
    ...

# For production environment
skills:
  - id: "prod_cluster_setup"
    name: "Production Cluster Setup"
    description: "Enterprise-grade production cluster deployment"
    ...
```

### 2. Different Organizations

Customize the provider information for different deployments:

```yaml
provider:
  organization: "Your Company"
  url: "https://yourcompany.com"
```

### 3. Extended Capabilities

Add more capabilities as the A2A protocol evolves:

```yaml
capabilities:
  streaming: true
  pushNotifications: true  # Enable when implemented
  stateTransitionHistory: true  # Enable when implemented
```

## Deployment

When deploying the Lightspeed service:

1. Ensure the agent card YAML file is accessible at the path specified in `agent_card_path`
2. Mount the file in your container/pod (similar to how `systemprompt.txt` is mounted)
3. Update the configuration to reference the correct path

Example pod volume mount:
```yaml
volumeMounts:
  - name: config-volume
    mountPath: /tmp/agentcard.yaml
    subPath: agentcard.yaml
```

## Validation

The agent card is validated when the service starts. If the YAML file is malformed or the path is incorrect, the service will fail to start with an error message indicating the issue.

## Related Files

- Configuration model: `lightspeed-stack/src/models/config.py`
- A2A endpoint implementation: `lightspeed-stack/src/app/endpoints/a2a.py`
- Example agent card: `config/agentcard.yaml`
- Configuration file: `config/lightspeed-stack.yaml`

