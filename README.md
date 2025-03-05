# Xircuits MCP Component Library

A Xircuits component library for implementing Model Context Protocol (MCP) servers. This library provides components that make it easy to create, configure, and run MCP servers using the Xircuits visual programming interface.

## What is Model Context Protocol (MCP)?

The [Model Context Protocol (MCP)](https://modelcontextprotocol.io) lets you build servers that expose data and functionality to LLM applications in a secure, standardized way. Think of it like a web API, but specifically designed for LLM interactions. MCP servers can:

- Expose data through **Resources** (think of these sort of like GET endpoints; they are used to load information into the LLM's context)
- Provide functionality through **Tools** (sort of like POST endpoints; they are used to execute code or otherwise produce a side effect)
- Define interaction patterns through **Prompts** (reusable templates for LLM interactions)
- And more!

## Prerequisites

- Python 3.8 or higher
- Xircuits
- MCP Python SDK

## Installation

To use this component library, ensure you have Xircuits installed, then simply run:

```
xircuits install https://github.com/xpressai/xai-mcp
```

Alternatively, you may manually copy the directory / clone or submodule the repository to your working Xircuits project directory then install the packages using:

```
pip install -r requirements.txt
```

## Components

This library provides components for implementing MCP servers, organized into several categories:

### Server Setup Components

- **MCPCreateServer**: Creates a FastMCP server instance with the specified name and optional dependencies.
- **MCPServerLifespan**: Sets up a lifespan context manager for the MCP server to handle startup and shutdown operations.
- **MCPRunServer**: Starts the MCP server and keeps it running until interrupted.

### Start Node Components

These components act as entry points for defining MCP server capabilities. They can be dragged onto the canvas to implement responses to events:

- **MCPDefineTool** (Start Node): Defines a tool for the MCP server, allowing LLMs to perform actions and computations.
- **MCPDefineResource** (Start Node): Defines a resource for the MCP server, allowing LLMs to access data through URI patterns.
- **MCPDefinePrompt** (Start Node): Defines a prompt template for the MCP server, providing reusable interaction patterns for LLMs.

### Result Setting Components

These components are used within the body of start nodes to set the results of tool, resource, or prompt executions:

- **MCPSetToolResult**: Sets the result of a tool execution.
- **MCPSetResourceResult**: Sets the result of a resource execution.
- **MCPSetPromptResult**: Sets the result of a prompt execution.

### Utility Components

- **MCPCreateImage**: Creates an Image object for use with MCP tools and resources.
- **MCPGetArgument**: Gets an argument from the args dictionary.
- **MCPReportProgress**: Reports progress for a long-running operation.
- **MCPReadResource**: Reads a resource from the MCP server.
- **MCPCreateUserMessage**: Creates a user message for use in prompts.
- **MCPCreateAssistantMessage**: Creates an assistant message for use in prompts.
- **MCPCreateMessageList**: Creates a list of messages for use in prompts.

## Usage Example

Here's an example of how to use this component library to create an MCP server:

1. Create a new Xircuits workflow
2. Add an **MCPCreateServer** component to create a server instance
3. Add **MCPDefineTool**, **MCPDefineResource**, and **MCPDefinePrompt** start nodes to define the server's capabilities
4. For each start node, connect components to implement the logic for the tool, resource, or prompt
5. Use **MCPSetToolResult**, **MCPSetResourceResult**, or **MCPSetPromptResult** to set the results
6. Add an **MCPRunServer** component to start the server

## Example: Creating a Calculator Tool

1. Drag an **MCPDefineTool** start node onto the canvas
2. Set its name to "add" and description to "Add two numbers"
3. Connect an **MCPGetArgument** component to get the "a" argument
4. Connect another **MCPGetArgument** component to get the "b" argument
5. Connect a component that adds the two numbers
6. Connect an **MCPSetToolResult** component to set the result

## Documentation

- [Model Context Protocol documentation](https://modelcontextprotocol.io)
- [Model Context Protocol specification](https://spec.modelcontextprotocol.io)
- [Officially supported servers](https://github.com/modelcontextprotocol/servers)

## License

Apache License 2.0
