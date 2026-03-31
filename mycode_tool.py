import glob as globlib 
import json, os, re, subprocess, urllib.request

RESET, BOLD, DIM = "\033[0m", "\033[1m", "\033[2m"
BLUE, CYAN, GREEN, YELLOW, RED = (
    "\033[34m",
    "\033[36m",
    "\033[32m",
    "\033[33m",
    "\033[31m",
)

def separator():
    return f"{DIM}{'─' * min(os.get_terminal_size().columns, 80)}{RESET}"

tools = [{
    "type": "function",
    "function": {
        "name": "read",
        "description": "Read file with line numbers (file path, not directory)",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "文件路径，不能是目录",
                },
                "offset": {
                    "type": "integer",
                    "description": "从第几行开始读取，默认为0",
                    "default": 0
                },
                "limit": {
                    "type": "integer",
                    "description": "最多读取多少行，默认为-1，表示读取全部",
                    "default": -1
                }
            },
            "required": ["path"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "write",
        "description": "Write content to file",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "文件路径，不能是目录",
                },
                "content": {
                    "type": "string",
                    "description": "要写入的内容",
                }
            },
            "required": ["path", "content"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "edit",
        "description": "Replace old with new in file (old must be unique unless all=true)",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "文件路径，不能是目录",
                },
                "old": {
                    "type": "string",
                    "description": "要被替换的内容",
                },
                "new": {
                    "type": "string",
                    "description": "新的内容",
                },
                "all": {
                    "type": "boolean",
                    "description": "是否替换所有匹配项，默认为false",
                    "default": False
                }
            },
            "required": ["path", "old", "new"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "glob",
        "description": "Find files by pattern, sorted by mtime",
        "parameters": {
            "type": "object",
            "properties": {
                "pat": {
                    "type": "string",
                    "description": "文件模式，支持通配符，比如*.txt",
                },
                "path": {
                    "type": "string",
                    "description": "搜索路径，默认为当前目录",
                }
            },
            "required": ["pat"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "grep",
        "description": "Search files for regex pattern",
        "parameters": {
            "type": "object",
            "properties": {
                "pat": {
                    "type": "string",
                    "description": "文件模式，支持通配符，比如*.txt",
                },
                "path": {
                    "type": "string",
                    "description": "搜索路径，默认为当前目录",
                }
            },
            "required": ["pat"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "bash",
        "description": "Run shell command",
        "parameters": {
            "type": "object",
            "properties": {
                "cmd": {
                    "type": "string",
                    "description": "要执行的shell命令",
                }
            },
            "required": ["cmd"]
        }
    }
}]





def read(path: str, offset:int=0, limit:int=-1):
    lines = open(path, encoding="utf-8").readlines()
    limit = len(lines) if limit < 0 else limit
    selected = lines[offset : offset + limit]
    # f"{num1:num2}" 其中 num1 是要格式化的数字，num2 是一个整数，表示 num1 最小占用的宽度。如果 num1 的位数不足 num2，则在前面补空格；如果 num1 的位数超过 num2，则直接输出 num1。
    return "".join(f"{offset + idx + 1:4}| {line}" for idx, line in enumerate(selected))


def write(path: str, content: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return "ok"


def edit(path: str, old: str, new: str, all: bool=False):
    text = open(path, encoding="utf-8").read()
    if old not in text:
        return "error: old_string not found"
    count = text.count(old)
    # 当既不能全局替换又出现多次匹配时，返回错误提示，要求old_string必须唯一，或者使用all=true来替换所有匹配项
    if not all and count > 1:
        return f"error: old_string appears {count} times, must be unique (use all=true)"
    replacement = (
        text.replace(old, new) if all else text.replace(old, new, 1)
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(replacement)
    return "ok"


def glob(pat: str, path: str="."):
    pattern = (path + "/" + pat).replace("//", "/")
    files = globlib.glob(pattern, recursive=True)
    files = sorted(
        files,
        key=lambda f: os.path.getmtime(f) if os.path.isfile(f) else 0,
        reverse=True,
    )
    return "\n".join(files) or "none"


def grep(pat: str, path: str="."):
    pattern = re.compile(pat)
    hits = []
    for filepath in globlib.glob(path + "/**", recursive=True):
        try:
            for line_num, line in enumerate(open(filepath, encoding="utf-8"), 1):
                if pattern.search(line):
                    hits.append(f"{filepath}:{line_num}:{line.rstrip()}")
        except Exception:
            pass
    return "\n".join(hits[:50]) or "none"


def bash(cmd: str):
    proc = subprocess.Popen(
        cmd, shell=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True
    )
    output_lines = []
    try:
        while True:
            line = proc.stdout.readline()
            if not line and proc.poll() is not None:
                break
            if line:
                print(f"  {DIM}│ {line.rstrip()}{RESET}", flush=True)
                output_lines.append(line)
        proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        proc.kill()
        output_lines.append("\n(timed out after 30s)")
    return "".join(output_lines).strip() or "(empty)"