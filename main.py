from pydantic import BaseModel, Field, ConfigDict
from typing import Callable
from openai import OpenAI
from os import getenv
from dotenv import load_dotenv
# import httpx
import os
import json
from copy import deepcopy

def basic_type_converter(t):
    if t == 'str':
        return 'string'
    if t == 'int' or t == 'float':
        return 'number'
    if t == 'list':
        return 'array'
    #TODO: more complicated processing for dictionary types

def get_func_desc(func):
    desc = ''
    vals = []
    for x in deepcopy(func.__doc__).split('\n'):
        if x != '':
            vals.append(x.strip())
    idx = vals.index('Args:')
    for x in vals[:idx]:
        desc += x
    return desc

def read_file(path: str) -> str:
    """
    Reads the content of a file.
    Args: 
    path: str: the path of the file to be read
    """
    try:
        with open(path, 'r') as f:
            return f.read()
    except Exception as e:
        return f"Error: {str(e)}"

def list_files(path: str = "") -> list[str]:
    """
    Lists the files in a directory.
    Defaults to the current working directory.
    Args:
    path: str: the directory path to list files from. Defaults to cwd if empty.
    """
    target = path or "."
    try:
        entries = os.listdir(target)
        return [
            f"{entry}" if os.path.isdir(os.path.join(target, entry)) else entry
            for entry in entries
        ]
    except Exception as e:
        return [f"Error: {str(e)}"]

def edit_file(path: str, old: str, new: str) -> str:
    """
    Replaces occurrences of old with new in file at path.
    Creates file if it does not exist.
    Args:
    path: str: the file path to edit or create.
    old: str: the substring to be replaced.
    new: str: the new substring to replace the old.
    """
    try:
        # Create file if it doesn't exist
        if not os.path.exists(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w') as f:
                f.write("")  # Create empty file
            return f"Created {path}"
        # Read existing file
        with open(path, 'r') as f:
            content = f.read()
        # Replace old with new
        new_content = content.replace(old, new)
        # Check if replacement actually happened
        if content == new_content:
            return "Error: old not found"
        # Write back to file
        with open(path, 'w') as f:
            f.write(new_content)
        return "Edit successful"
    except Exception as e:
        return f"Error: {str(e)}"

class ToolDefinition(BaseModel):
    function: Callable
    name: str = Field(default_factory=lambda data: data['function'].__name__)
    desc: str = Field(default_factory=lambda data: get_func_desc(data['function']))

    #TODO: fix no-argument, no-default tools not being supported
    def format_props(self):
        raw_props = []
        for x in deepcopy(self.function.__doc__.split('\n')):
            if x != '':
                raw_props.append(x.strip())
        idx = raw_props.index('Args:')+1
        props = {}
        for arg in raw_props[idx:]:
            name, ty, des = [x.strip() for x in arg.split(':')]
            props[name] = {"type": basic_type_converter(ty), "description": des}
        return props

    def format_req(self):
        ret = deepcopy(list(self.function.__annotations__.keys()))
        if 'return' in ret:
            ret.remove('return')
        return ret
    
    def format_tool(self):
        return json.dumps({
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.desc,
                "strict": True,
                "parameters": {
                    "type": "object",
                    "properties": self.format_props(),
                    "required": self.format_req(),
                    "additionalProperties": False
                }
            }
        })

class Agent(BaseModel):
    model_config=ConfigDict(arbitrary_types_allowed=True)

    client: OpenAI
    model: str #TODO: validate against openrouter API
    tools: dict[str, ToolDefinition]
    conversation: list[dict] = []

    def build_tool_schema(self):
        schemas = []
        for tool in self.tools.values():
            schemas.append(json.loads(tool.format_tool()))
        return schemas

    def user_message(self, user_in):
        return {
                "role": "user",
                "content": [{"type": "text", "text": user_in}]
            }

    def run(self):
        print(f"Chat with {self.model} (use 'quit' to quit)")
        while True:
            user_input = input("\033[94mYou: \033[0m").strip()
            if user_input.lower() == "quit":
                break

            self.conversation.append(self.user_message(user_input))

            response = self.get_llm_response()
            self.handle_response(response)

    def get_llm_response(self) -> 'openai.types.chat.chat_completion_message.ChatCompletionMessage':
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.conversation,
            tools=self.build_tool_schema(),
            tool_choice="auto"
        )
        self.conversation.append(response.choices[0].message.model_dump())
        return response

    def execute_single_tool_call(self, tool_call):
        """Execute a tool call and return the formatted response"""
        tool_name = tool_call.function.name
        tool_args = json.loads(tool_call.function.arguments)

        #check if tool exists
        if tool_name not in self.tools:
            return {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "name": tool_name,
            "content": f"Error: Unknown tool:{tool_name}",
        }
        #execute
        tool_func = self.tools[tool_name].function
        try:
            tool_result = tool_func(**tool_args)
        except Exception as e:
            tool_result = f"Tool execution error: {str(e)}"

        return {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "name": tool_name,
            "content": str(tool_result),
        }

    def handle_response(self, response):
        if response.choices[0].message.tool_calls:
            for tool_call in response.choices[0].message.tool_calls:
                tool_response = self.execute_single_tool_call(tool_call)
                self.conversation.append(tool_response)
            # Get another response from the LLM with the tool results
            new_response = self.get_llm_response()
            # Recursively handle the new response (in case it has more tool calls)
            self.handle_response(new_response)
        else:
            # No tool calls - this is the final response
            final_content = response.choices[0].message.content
            print(f"\033[92mAgent: \033[0m{final_content}")

def main():
    load_dotenv()

    # gets API Key from environment variable OPENROUTER_API_KEY
    cli = OpenAI(
      base_url="https://openrouter.ai/api/v1",
      api_key=getenv("OPENROUTER_API_KEY"),
    )
    test_model = 'anthropic/claude-sonnet-4'
    cat = ToolDefinition(function=read_file)
    ls = ToolDefinition(function=list_files)
    ed = ToolDefinition(function=edit_file)
    tool_dic = {"read_file": cat, "list_files": ls, "edit_file": ed}
    AUgent = Agent(client=cli, model=test_model, tools=tool_dic)
    AUgent.run()

if __name__ == "__main__":
    main()
