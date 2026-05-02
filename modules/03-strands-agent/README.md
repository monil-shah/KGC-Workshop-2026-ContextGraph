# Module 3: Building a Strands Agent

**Duration**: ~45 minutes

## What You'll Build

An AI agent using the **Strands Agents SDK** that can:
- Retrieve information from your Bedrock Knowledge Base
- Use custom tools to perform actions
- Maintain conversation context
- Orchestrate multi-step reasoning

## What is Strands Agents SDK?

[Strands](https://strandsagents.com) is an open-source, model-driven agent framework by AWS. Instead of hardcoding agent logic, you give the LLM tools and let it decide when and how to use them.

```python
from strands import Agent
from strands.models.bedrock import BedrockModel
from strands_tools import retrieve

agent = Agent(model=BedrockModel(), tools=[retrieve])
agent("What metrics track PO aging for LLE?")
```

That's it. The agent:
1. Receives your question
2. Decides it needs to search the knowledge base
3. Calls the `retrieve` tool
4. Reads the results
5. Generates a grounded answer

## Step 1: Build a Simple Agent

```bash
python code/simple_agent.py
```

This creates a basic agent with the `retrieve` tool connected to your Knowledge Base. Try asking it questions about the company policies.

## Step 2: Add Custom Tools

```bash
python code/agent_with_tools.py
```

We add custom tools using the `@tool` decorator:
- `get_period_info` — Returns current accounting period and close deadlines
- `classify_risk` — Classifies financial risk level for POs/assets
- `check_grc_control` — Looks up GRC control details

## Step 3: Build a Multi-Agent System

```bash
python code/multi_agent.py
```

This creates a system with:
- **Router Agent** — Classifies intent and delegates to specialists
- **Metrics Agent** — Answers questions about metric definitions and namespaces
- **Reconciliation Agent** — Answers questions about matching rules and tolerances
- **Compliance Agent** — Answers questions about SOX, GRC, and close procedures

The agents use the **agents-as-tools** pattern: the router agent calls specialist agents as if they were tools.

## Step 4: Interactive Chat

```bash
python code/chat.py
```

An interactive chat session where you can talk to the multi-agent system. Type `quit` to exit.

## How Strands Works

```
User Input
    │
    ▼
┌─────────────────────────────┐
│         Agent Loop          │
│                             │
│  1. Send to LLM             │
│  2. LLM decides: respond    │
│     or use a tool           │
│  3. If tool: execute it     │
│  4. Feed result back to LLM │
│  5. Repeat until done       │
│                             │
└─────────────────────────────┘
    │
    ▼
Final Response
```

### The @tool Decorator

```python
from strands import tool

@tool
def get_weather(city: str) -> str:
    """Get the current weather for a city.

    Args:
        city: The city name to look up weather for.
    """
    # Your implementation here
    return f"Weather in {city}: 72°F, sunny"
```

The docstring becomes the tool description the LLM sees. Argument types and descriptions help the LLM call the tool correctly.

### Multi-Agent Patterns

Strands supports several patterns:

| Pattern | Description | Use Case |
|---------|-------------|----------|
| **Agents-as-Tools** | Agents call other agents like tools | Hierarchical delegation |
| **Swarms** | Agents hand off to peers autonomously | Collaborative problem-solving |
| **Graphs** | Deterministic workflow with conditional routing | Structured pipelines |

## Key Takeaways

- Strands is model-driven: the LLM decides tool usage, not your code
- The `@tool` decorator turns any Python function into an agent tool
- The built-in `retrieve` tool connects directly to Bedrock Knowledge Bases
- Multi-agent systems let you specialize agents for different domains
- Conversation context is maintained automatically within a session

## Next

→ [Module 4: Context Graph](../04-context-graph/) — Build a graph to solve the two clock problem
