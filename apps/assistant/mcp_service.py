import requests
import json
import logging
import asyncio
import shlex
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)

class MCPService:
    """
    MCP (Model Context Protocol) Service for interacting with MCP servers.
    Supports both Remote (HTTP/SSE) and Local (Stdio) transports.
    """
    
    @staticmethod
    def get_tools(api_url, api_key=None, mcp_type='remote'):
        """
        Fetch tools from an MCP server.
        """
        if mcp_type == 'local':
            return asyncio.run(MCPService._get_tools_local(api_url))
            
        headers = {'Content-Type': 'application/json'}
        if api_key:
            headers['Authorization'] = f'Bearer {api_key}'
        
        try:
            response = requests.get(f"{api_url.rstrip('/')}/tools", headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to fetch MCP tools: {response.status_code} - {response.text}")
                return {"error": f"Server returned {response.status_code}"}
        except Exception as e:
            logger.error(f"Error connecting to MCP server: {str(e)}")
            return {"error": str(e)}

    @staticmethod
    async def _get_tools_local(command_str):
        """Internal method to fetch tools from a local MCP server using stdio."""
        try:
            # Parse command
            args = shlex.split(command_str)
            server_params = StdioServerParameters(
                command=args[0],
                args=args[1:],
                env=None
            )
            
            # Use a timeout for the entire operation
            async with asyncio.timeout(30):
                async with stdio_client(server_params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        tools = await session.list_tools()
                        # Convert to list of dicts for frontend
                        return [
                            {"name": t.name, "description": t.description, "input_schema": t.inputSchema}
                            for t in tools.tools
                        ]
        except Exception as e:
            logger.error(f"Local MCP Error: {str(e)}")
            return {"error": str(e)}

    @staticmethod
    def call_tool(api_url, tool_name, arguments, api_key=None, mcp_type='remote'):
        """
        Call a specific tool on an MCP server.
        """
        if mcp_type == 'local':
            return asyncio.run(MCPService._call_tool_local(api_url, tool_name, arguments))

        headers = {'Content-Type': 'application/json'}
        if api_key:
            headers['Authorization'] = f'Bearer {api_key}'
            
        payload = {
            "jsonrpc": "2.0",
            "method": "call_tool",
            "params": {
                "name": tool_name,
                "arguments": arguments
            },
            "id": 1
        }
        
        try:
            response = requests.post(f"{api_url.rstrip('/')}/call", headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to call MCP tool {tool_name}: {response.status_code} - {response.text}")
                return {"error": f"Server returned {response.status_code}"}
        except Exception as e:
            logger.error(f"Error calling MCP tool {tool_name}: {str(e)}")
            return {"error": str(e)}

    @staticmethod
    async def _call_tool_local(command_str, tool_name, arguments):
        """Internal method to call a local MCP tool using stdio."""
        try:
            args = shlex.split(command_str)
            server_params = StdioServerParameters(
                command=args[0],
                args=args[1:],
                env=None
            )
            
            async with asyncio.timeout(60):
                async with stdio_client(server_params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        result = await session.call_tool(tool_name, arguments)
                        # Convert result to JSON-serializable format
                        return {
                            "content": [
                                {"type": c.type, "text": c.text} if hasattr(c, 'text') else {"type": c.type}
                                for c in result.content
                            ],
                            "isError": result.isError
                        }
        except Exception as e:
            logger.error(f"Local MCP Call Error: {str(e)}")
            return {"error": str(e)}
