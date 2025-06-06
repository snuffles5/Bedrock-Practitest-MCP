# client.py
import asyncio
import sys
from os import environ
from typing import Optional, List, Dict, Any
from contextlib import AsyncExitStack
from dataclasses import dataclass

# to interact with MCP
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# to interact with Amazon Bedrock
import boto3

AWS_ACCESS_KEY_ID = environ.get("AWS_ACCESS_KEY_ID", "your_api_token_here")  # Replace with your actual token
AWS_SECRET_ACCESS_KEY = environ.get("AWS_SECRET_ACCESS_KEY", "your_api_token_here")  # Replace with your actual token
AWS_SESSION_TOKEN = environ.get("AWS_SESSION_TOKEN", "your_api_token_here")  # Replace with your actual token
# client.py
@dataclass
class Message:
    role: str
    content: List[Dict[str, Any]]

    @classmethod
    def user(cls, text: str) -> 'Message':
        return cls(role="user", content=[{"text": text}])

    @classmethod
    def assistant(cls, text: str) -> 'Message':
        return cls(role="assistant", content=[{"text": text}])

    @classmethod
    def tool_result(cls, tool_use_id: str, content: dict) -> 'Message':
        return cls(
            role="user",
            content=[{
                "toolResult": {
                    "toolUseId": tool_use_id,
                    "content": [{"json": {"text": content[0].text}}]
                }
            }]
        )

    @classmethod
    def tool_request(cls, tool_use_id: str, name: str, input_data: dict) -> 'Message':
        return cls(
            role="assistant",
            content=[{
                "toolUse": {
                    "toolUseId": tool_use_id,
                    "name": name,
                    "input": input_data
                }
            }]
        )

    @staticmethod
    def to_bedrock_format(tools_list: List[Dict]) -> List[Dict]:
        return [{
            "toolSpec": {
                "name": tool["name"],
                "description": tool["description"],
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": tool["input_schema"]["properties"],
                        "title": tool["input_schema"]["title"]
                    }
                }
            }
        } for tool in tools_list]


# client.py
class MCPClient:
    MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"

    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        session = boto3.Session(
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            aws_session_token=AWS_SESSION_TOKEN,
            region_name='us-east-1'  # change if needed
        )

        self.bedrock = session.client('bedrock-runtime')


    async def connect_to_server(self, server_script_path: str):
        if not server_script_path.endswith(('.py', '.js')):
            raise ValueError("Server script must be a .py or .js file")

        command = "python" if server_script_path.endswith('.py') else "node"
        server_params = StdioServerParameters(command=command, args=[server_script_path], env=None)

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        await self.session.initialize()

        response = await self.session.list_tools()
        print("\nConnected to server with tools:", [tool.name for tool in response.tools])

    async def cleanup(self):
        await self.exit_stack.aclose()

    # client.py
    def _make_bedrock_request(self, messages: List[Dict], tools: List[Dict]) -> Dict:
        return self.bedrock.converse(
            modelId=self.MODEL_ID,
            messages=messages,
            inferenceConfig={"maxTokens": 1000, "temperature": 0},
            toolConfig={"tools": tools}
        )

    async def process_query(self, query: str) -> str:
        # (1)
        pre_prompt = Message.user("""
You are a helpful assistant. Use tools only when necessary.
Use the get_instances tool to retrieve a list of test instances from Practitest.
    It requires no input. Each instance includes basic info like assigned user, 
    environment, vendor, provider, feature, last run status, and time.
Use the get_instance_runs tool to retrieve details of a specific test run. 
    It requires an instance ID as input, which must be obtained from get_instances. 
    It returns data like run status, creation time, and a Jenkins job link.
If user asks for runs of a specific instance, 
    first call get_instances to get the instance ID, then call get_instance_runs with that ID.
    the get_instances tool returns only 1 last run and not all runs of the instance.
""")
        messages = [pre_prompt.__dict__, Message.user(query).__dict__]
        # (2)
        response = await self.session.list_tools()

        # (3)
        available_tools = [{
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        } for tool in response.tools]

        bedrock_tools = Message.to_bedrock_format(available_tools)

        # (4)
        response = self._make_bedrock_request(messages, bedrock_tools)

        # (6)
        return await self._process_response(  # (5)
            response, messages, bedrock_tools
        )

    # client.py

    async def _process_response(self, response: Dict, messages: List[Dict], bedrock_tools: List[Dict]) -> str:
        # (1)
        final_text = []
        MAX_TURNS = 10
        turn_count = 0

        while True:
            # (2)
            if response['stopReason'] == 'tool_use':
                final_text.append("received toolUse request")
                for item in response['output']['message']['content']:
                    if 'text' in item:
                        final_text.append(f"[Thinking: {item['text']}]")
                        messages.append(Message.assistant(item['text']).__dict__)
                    elif 'toolUse' in item:
                        # (3)
                        tool_info = item['toolUse']
                        result = await self._handle_tool_call(tool_info, messages)
                        final_text.extend(result)

                        response = self._make_bedrock_request(messages, bedrock_tools)
            # (4)
            elif response['stopReason'] == 'max_tokens':
                final_text.append("[Max tokens reached, ending conversation.]")
                break
            elif response['stopReason'] == 'stop_sequence':
                final_text.append("[Stop sequence reached, ending conversation.]")
                break
            elif response['stopReason'] == 'content_filtered':
                final_text.append("[Content filtered, ending conversation.]")
                break
            elif response['stopReason'] == 'end_turn':
                final_text.append(response['output']['message']['content'][0]['text'])
                break

            turn_count += 1

            if turn_count >= MAX_TURNS:
                final_text.append("\n[Max turns reached, ending conversation.]")
                break
        # (5)
        return "\n\n".join(final_text)

    # client.py

    async def _handle_tool_call(self, tool_info: Dict, messages: List[Dict]) -> List[str]:
        # (1)
        tool_name = tool_info['name']
        tool_args = tool_info['input']
        tool_use_id = tool_info['toolUseId']

        # (2)
        result = await self.session.call_tool(tool_name, tool_args)

        # (3)
        messages.append(Message.tool_request(tool_use_id, tool_name, tool_args).__dict__)
        messages.append(Message.tool_result(tool_use_id, result.content).__dict__)

        # (4)
        return [f"[Calling tool {tool_name} with args {tool_args}]"]

    # client.py

    async def chat_loop(self):
        print("\nMCP Client Started!\nType your queries or 'quit' to exit.")
        while True:
            try:
                query = input("\nQuery: ").strip()
                if query.lower() == 'quit':
                    break
                response = await self.process_query(query)
                print("\n" + response)
            except Exception as e:
                print(f"\nError: {str(e)}")


# client.py
async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        sys.exit(1)

    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
