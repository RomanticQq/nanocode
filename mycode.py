import os
import json
from openai import OpenAI
from mycode_tool import tools, separator
from mycode_tool import write, read, edit, glob, grep, bash
from mycode_tool import RESET, BOLD, DIM, BLUE, CYAN, GREEN, YELLOW, RED


tool_mapping = {
    "read": read,
    "write": write,
    "edit": edit,
    "glob": glob,
    "grep": grep,
    "bash": bash
}
client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")

def call_api(messages):
    response = client.chat.completions.create(
        model="qwen3.5-plus",
        messages=messages,
        stream=False,
        tool_choice="auto",
        tools=tools,
    )
    return response

messages = [
    {"role": "system", "content": f"Concise coding assistant. cwd: {os.getcwd()}"}
]
while True:
    try:
        print(separator())
        user_input = input(f"{BOLD}{BLUE}❯{RESET} ").strip()
        # user_input = "请创建一个a.py文件，并写一个代码去打印hello world"
        print(separator())
        if not user_input:
            continue
        if user_input in ("/q", "exit"):
            break
        if user_input == "/c":
            messages = [{"role": "system", "content": f"Concise coding assistant. cwd: {os.getcwd()}"}]
            print(f"{GREEN}⏺ Cleared conversation{RESET}")
            continue
        messages.append({"role": "user", "content": user_input})

        while True:
            response = call_api(messages)
            message = response.choices[0].message
            messages.append(message)
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    print("工具调用：", tool_call)
                    function_name = tool_call.function.name
                    function_args = tool_call.function.arguments
                    function_id = tool_call.id
                    function = tool_mapping[function_name]
                    function_args_dict = json.loads(function_args)
                    function_result = function(**function_args_dict)
                    tool_message = {
                        "tool_call_id": function_id,
                        "role": "tool",
                        "name": function_name,
                        "content": function_result,
                    }
                    messages.append(tool_message)
            else:
                content = message.content
                print(content)
                break
    except (KeyboardInterrupt, EOFError):
        break
    except Exception as err:
        print(f"{RED}⏺ Error: {err}{RESET}")