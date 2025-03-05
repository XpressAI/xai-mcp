from xai_components.base import InArg, OutArg, InCompArg, Component, BaseComponent, xai_component, SubGraphExecutor, dynalist
import json
import sys
import os

# Context keys for MCP server
MCP_SERVER_KEY = 'mcp_server'
MCP_TOOLS_KEY = 'mcp_tools'
MCP_RESOURCES_KEY = 'mcp_resources'
MCP_PROMPTS_KEY = 'mcp_prompts'

@xai_component
class MCPCreateServer(Component):
    """
    Creates a FastMCP server instance for implementing Model Context Protocol (MCP) servers.
    
    This component provides the foundation for creating MCP servers in Xircuits.
    
    ##### inPorts:
    - server_name (str): The name of the MCP server.
    - dependencies (list): Optional list of dependencies required by the server.
    """
    server_name: InCompArg[str]
    dependencies: InArg[list]
    
    def execute(self, ctx) -> None:
        try:
            from mcp.server.fastmcp import FastMCP
        except ImportError:
            print("Error: Model Context Protocol SDK not installed.")
            print("Please install it with: pip install mcp")
            return
            
        name = self.server_name.value
        dependencies = self.dependencies.value or []
        
        if not name:
            name = "xircuits-mcp-server"
            
        server = FastMCP(name, dependencies=dependencies)
        
        print(f"Created MCP server: {name}")
        if dependencies:
            print(f"With dependencies: {', '.join(dependencies)}")
            
        ctx[MCP_SERVER_KEY] = server


@xai_component
class MCPServerLifespan(Component):
    """
    Sets up a lifespan context manager for the MCP server.
    
    ##### inPorts:
    - startup_code (str): Python code to execute on server startup.
    - shutdown_code (str): Python code to execute on server shutdown.
    """
    startup_code: InArg[str]
    shutdown_code: InArg[str]
    
    def execute(self, ctx) -> None:
        if MCP_SERVER_KEY not in ctx:
            print("Error: MCP server not found in context. Please create a server first.")
            return
            
        server = ctx[MCP_SERVER_KEY]
        startup_code = self.startup_code.value or ""
        shutdown_code = self.shutdown_code.value or ""
        
        try:
            from contextlib import asynccontextmanager
            from typing import AsyncIterator
            
            # Create a namespace for the lifespan function
            namespace = {}
            
            # Add necessary imports to the namespace
            exec("from contextlib import asynccontextmanager", namespace)
            exec("from typing import AsyncIterator", namespace)
            
            # Define the lifespan function
            lifespan_code = f"""
@asynccontextmanager
async def server_lifespan(server) -> AsyncIterator[dict]:
    \"\"\"Manage server startup and shutdown lifecycle.\"\"\"
    try:
        # Initialize resources on startup
{startup_code}
        yield {"{}"} # Context dictionary
    finally:
        # Clean up on shutdown
{shutdown_code}
"""
            
            # Execute the code to define the lifespan function
            exec(lifespan_code, namespace)
            
            # Get the lifespan function from the namespace
            lifespan_function = namespace["server_lifespan"]
            
            # Set the lifespan on the server
            server.lifespan = lifespan_function
            
            print("Configured server lifespan")
        except Exception as e:
            print(f"Error configuring server lifespan: {e}")


@xai_component
class MCPRunServer(Component):
    """
    Runs the MCP server.
    """
    
    def execute(self, ctx) -> None:
        if MCP_SERVER_KEY not in ctx:
            print("Error: MCP server not found in context. Please create a server first.")
            return
            
        server = ctx[MCP_SERVER_KEY]
            
        try:
            print("Starting MCP server...")
            
            # Register all tools, resources, and prompts
            for tool in ctx.get(MCP_TOOLS_KEY, []):
                # The tool registration is handled in the init method of the tool component
                pass
                
            for resource in ctx.get(MCP_RESOURCES_KEY, []):
                # The resource registration is handled in the init method of the resource component
                pass
                
            for prompt in ctx.get(MCP_PROMPTS_KEY, []):
                # The prompt registration is handled in the init method of the prompt component
                pass
            
            # Run the server
            server.run()
            
        except Exception as e:
            print(f"Error running MCP server: {e}")


@xai_component(type='Start', color='#4169E1')  # Royal Blue for tools
class MCPDefineTool(Component):
    """
    Defines a tool for the MCP server.
    
    ##### inPorts:
    - name (str): The name of the tool.
    - description (str): A description of what the tool does.
    
    ##### outPorts:
    - args: The arguments passed to the tool.
    - ctx: The MCP context object.
    """
    name: InCompArg[str]
    description: InArg[str]
    
    args: OutArg[dict]
    ctx: OutArg[Any]
    
    def init(self, ctx):
        if MCP_SERVER_KEY not in ctx:
            print(f"Warning: MCP server not found in context when registering tool '{self.name.value}'. Tool will be registered when server is created.")
        
        ctx.setdefault(MCP_TOOLS_KEY, []).append(self)
        
        # If server already exists, register the tool immediately
        if MCP_SERVER_KEY in ctx:
            self._register_tool(ctx)
    
    def _register_tool(self, ctx):
        server = ctx[MCP_SERVER_KEY]
        
        # Create a wrapper function that will execute the tool's body
        def tool_handler(*args, **kwargs):
            # Extract the docstring from the description
            docstring = self.description.value or ""
            
            # Create a new context for the tool execution
            tool_ctx = ctx.copy()
            
            # Set the args and ctx outputs
            self.args.value = kwargs
            self.ctx.value = kwargs.get('ctx')
            
            # Execute the component chain starting from self.next
            result = None
            if hasattr(self, 'next') and self.next:
                # Execute the component chain and capture the result
                SubGraphExecutor(self.next).do(tool_ctx)
                # The result should be set in the tool_ctx by a component in the chain
                result = tool_ctx.get('tool_result')
            
            return result
        
        # Set the docstring
        tool_handler.__doc__ = self.description.value
        
        # Register the tool with the server
        if self.name.value:
            server._tool(name=self.name.value)(tool_handler)
        else:
            server._tool()(tool_handler)
        
        print(f"Registered tool: {self.name.value}")


@xai_component(type='Start', color='#32CD32')  # Lime Green for resources
class MCPDefineResource(Component):
    """
    Defines a resource for the MCP server.
    
    ##### inPorts:
    - path (str): The URI pattern for the resource (e.g., "users://{user_id}/profile").
    - description (str): A description of what the resource provides.
    
    ##### outPorts:
    - args: The arguments extracted from the resource path.
    - ctx: The MCP context object.
    """
    path: InCompArg[str]
    description: InArg[str]
    
    args: OutArg[dict]
    ctx: OutArg[Any]
    
    def init(self, ctx):
        if MCP_SERVER_KEY not in ctx:
            print(f"Warning: MCP server not found in context when registering resource '{self.path.value}'. Resource will be registered when server is created.")
        
        ctx.setdefault(MCP_RESOURCES_KEY, []).append(self)
        
        # If server already exists, register the resource immediately
        if MCP_SERVER_KEY in ctx:
            self._register_resource(ctx)
    
    def _register_resource(self, ctx):
        server = ctx[MCP_SERVER_KEY]
        
        # Create a wrapper function that will execute the resource's body
        def resource_handler(*args, **kwargs):
            # Extract the docstring from the description
            docstring = self.description.value or ""
            
            # Create a new context for the resource execution
            resource_ctx = ctx.copy()
            
            # Set the args and ctx outputs
            self.args.value = kwargs
            self.ctx.value = kwargs.get('ctx')
            
            # Execute the component chain starting from self.next
            result = None
            if hasattr(self, 'next') and self.next:
                # Execute the component chain and capture the result
                SubGraphExecutor(self.next).do(resource_ctx)
                # The result should be set in the resource_ctx by a component in the chain
                result = resource_ctx.get('resource_result')
            
            return result
        
        # Set the docstring
        resource_handler.__doc__ = self.description.value
        
        # Register the resource with the server
        server._resource(self.path.value)(resource_handler)
        
        print(f"Registered resource: {self.path.value}")


@xai_component(type='Start', color='#9932CC')  # Dark Orchid for prompts
class MCPDefinePrompt(Component):
    """
    Defines a prompt for the MCP server.
    
    ##### inPorts:
    - name (str): The name of the prompt.
    - description (str): A description of what the prompt does.
    
    ##### outPorts:
    - args: The arguments passed to the prompt.
    - ctx: The MCP context object.
    """
    name: InCompArg[str]
    description: InArg[str]
    
    args: OutArg[dict]
    ctx: OutArg[Any]
    
    def init(self, ctx):
        if MCP_SERVER_KEY not in ctx:
            print(f"Warning: MCP server not found in context when registering prompt '{self.name.value}'. Prompt will be registered when server is created.")
        
        ctx.setdefault(MCP_PROMPTS_KEY, []).append(self)
        
        # If server already exists, register the prompt immediately
        if MCP_SERVER_KEY in ctx:
            self._register_prompt(ctx)
    
    def _register_prompt(self, ctx):
        server = ctx[MCP_SERVER_KEY]
        
        # Create a wrapper function that will execute the prompt's body
        def prompt_handler(*args, **kwargs):
            # Extract the docstring from the description
            docstring = self.description.value or ""
            
            # Create a new context for the prompt execution
            prompt_ctx = ctx.copy()
            
            # Set the args and ctx outputs
            self.args.value = kwargs
            self.ctx.value = kwargs.get('ctx')
            
            # Execute the component chain starting from self.next
            result = None
            if hasattr(self, 'next') and self.next:
                # Execute the component chain and capture the result
                SubGraphExecutor(self.next).do(prompt_ctx)
                # The result should be set in the prompt_ctx by a component in the chain
                result = prompt_ctx.get('prompt_result')
            
            return result
        
        # Set the docstring
        prompt_handler.__doc__ = self.description.value
        
        # Register the prompt with the server
        if self.name.value:
            server._prompt(name=self.name.value)(prompt_handler)
        else:
            server._prompt()(prompt_handler)
        
        print(f"Registered prompt: {self.name.value}")


@xai_component(color='#4169E1')  # Royal Blue for tools
class MCPSetToolResult(Component):
    """
    Sets the result of a tool execution.
    
    ##### inPorts:
    - result: The result to return from the tool.
    """
    result: InArg[Any]
    
    def execute(self, ctx) -> None:
        ctx['tool_result'] = self.result.value
        print(f"Set tool result: {self.result.value}")


@xai_component(color='#32CD32')  # Lime Green for resources
class MCPSetResourceResult(Component):
    """
    Sets the result of a resource execution.
    
    ##### inPorts:
    - result: The result to return from the resource.
    """
    result: InArg[Any]
    
    def execute(self, ctx) -> None:
        ctx['resource_result'] = self.result.value
        print(f"Set resource result: {self.result.value}")


@xai_component(color='#9932CC')  # Dark Orchid for prompts
class MCPSetPromptResult(Component):
    """
    Sets the result of a prompt execution.
    
    ##### inPorts:
    - result: The result to return from the prompt.
    """
    result: InArg[Any]
    
    def execute(self, ctx) -> None:
        ctx['prompt_result'] = self.result.value
        print(f"Set prompt result: {self.result.value}")


@xai_component
class MCPCreateImage(Component):
    """
    Creates an Image object for use with MCP tools and resources.
    
    ##### inPorts:
    - image_path (str): Path to the image file.
    - format (str): Image format (e.g., "png", "jpeg"). If not provided, it will be inferred from the file extension.
    
    ##### outPorts:
    - image: The MCP Image object.
    """
    image_path: InArg[str]
    format: InArg[str]
    image: OutArg[Any]
    
    def execute(self, ctx) -> None:
        image_path = self.image_path.value
        format = self.format.value
        
        if not image_path:
            print("Error: Image path is required")
            return
            
        try:
            from mcp.server.fastmcp import Image
            import os
            
            # Infer format from file extension if not provided
            if not format:
                _, ext = os.path.splitext(image_path)
                format = ext.lstrip('.').lower()
                if not format:
                    format = "png"  # Default format
            
            # Read image data
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # Create Image object
            image = Image(data=image_data, format=format)
            
            print(f"Created Image object from {image_path}")
            self.image.value = image
        except Exception as e:
            print(f"Error creating Image object: {e}")


@xai_component
class MCPGetArgument(Component):
    """
    Gets an argument from the args dictionary.
    
    ##### inPorts:
    - args (dict): The arguments dictionary.
    - key (str): The key of the argument to get.
    - default: The default value to return if the key is not found.
    
    ##### outPorts:
    - value: The value of the argument.
    """
    args: InArg[dict]
    key: InArg[str]
    default: InArg[Any]
    
    value: OutArg[Any]
    
    def execute(self, ctx) -> None:
        args = self.args.value
        key = self.key.value
        default = self.default.value
        
        if not args:
            print("Warning: Args dictionary is empty or None")
            self.value.value = default
            return
            
        if not key:
            print("Error: Key is required")
            return
            
        self.value.value = args.get(key, default)


@xai_component
class MCPReportProgress(Component):
    """
    Reports progress for a long-running operation.
    
    ##### inPorts:
    - ctx: The MCP context object.
    - current (int): The current progress value.
    - total (int): The total progress value.
    - message (str): An optional message to include with the progress report.
    """
    ctx_obj: InArg[Any]
    current: InArg[int]
    total: InArg[int]
    message: InArg[str]
    
    def execute(self, ctx) -> None:
        ctx_obj = self.ctx_obj.value
        current = self.current.value
        total = self.total.value
        message = self.message.value
        
        if not ctx_obj:
            print("Error: MCP context object is required")
            return
            
        if current is None or total is None:
            print("Error: Current and total progress values are required")
            return
            
        try:
            # Report progress
            if message:
                ctx_obj.info(message)
            
            ctx_obj.report_progress(current, total)
            
            print(f"Reported progress: {current}/{total}")
        except Exception as e:
            print(f"Error reporting progress: {e}")


@xai_component
class MCPReadResource(Component):
    """
    Reads a resource from the MCP server.
    
    ##### inPorts:
    - ctx: The MCP context object.
    - uri (str): The URI of the resource to read.
    
    ##### outPorts:
    - data: The resource data.
    - mime_type: The MIME type of the resource.
    """
    ctx_obj: InArg[Any]
    uri: InArg[str]
    
    data: OutArg[Any]
    mime_type: OutArg[str]
    
    def execute(self, ctx) -> None:
        ctx_obj = self.ctx_obj.value
        uri = self.uri.value
        
        if not ctx_obj:
            print("Error: MCP context object is required")
            return
            
        if not uri:
            print("Error: Resource URI is required")
            return
            
        try:
            # Read the resource
            data, mime_type = ctx_obj.read_resource(uri)
            
            self.data.value = data
            self.mime_type.value = mime_type
            
            print(f"Read resource: {uri}")
        except Exception as e:
            print(f"Error reading resource: {e}")


@xai_component
class MCPCreateUserMessage(Component):
    """
    Creates a user message for use in prompts.
    
    ##### inPorts:
    - content (str): The content of the message.
    
    ##### outPorts:
    - message: The user message object.
    """
    content: InArg[str]
    message: OutArg[Any]
    
    def execute(self, ctx) -> None:
        content = self.content.value
        
        if not content:
            print("Error: Message content is required")
            return
            
        try:
            from mcp.server.fastmcp import UserMessage
            
            # Create the message
            message = UserMessage(content)
            
            self.message.value = message
            
            print(f"Created user message: {content[:50]}...")
        except Exception as e:
            print(f"Error creating user message: {e}")


@xai_component
class MCPCreateAssistantMessage(Component):
    """
    Creates an assistant message for use in prompts.
    
    ##### inPorts:
    - content (str): The content of the message.
    
    ##### outPorts:
    - message: The assistant message object.
    """
    content: InArg[str]
    message: OutArg[Any]
    
    def execute(self, ctx) -> None:
        content = self.content.value
        
        if not content:
            print("Error: Message content is required")
            return
            
        try:
            from mcp.server.fastmcp import AssistantMessage
            
            # Create the message
            message = AssistantMessage(content)
            
            self.message.value = message
            
            print(f"Created assistant message: {content[:50]}...")
        except Exception as e:
            print(f"Error creating assistant message: {e}")


@xai_component
class MCPCreateMessageList(Component):
    """
    Creates a list of messages for use in prompts.
    
    ##### inPorts:
    - messages (list): A list of message objects.
    
    ##### outPorts:
    - message_list: The list of messages.
    """
    messages: InArg[list]
    message_list: OutArg[list]
    
    def execute(self, ctx) -> None:
        messages = self.messages.value
        
        if not messages:
            print("Warning: Messages list is empty or None")
            self.message_list.value = []
            return
            
        self.message_list.value = messages
        
        print(f"Created message list with {len(messages)} messages")
