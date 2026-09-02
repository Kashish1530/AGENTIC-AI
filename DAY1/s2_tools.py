import os
import json
import sqlite3
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.environ["GROQ_API_KEY"])
MODEL = "openai/gpt-oss-120b"

# ---------- 1. web_search (mocked) ----------
def web_search(query):
    # Replace with a real API (e.g. Tavily, SerpAPI) later if you want.
    return f"[MOCK DATA — not real search results] Placeholder results for '{query}': [result 1, result 2, result 3]"

# ---------- 2. read_file ----------
def read_file(path):
    try:
        with open(path, "r") as f:
            return f.read()[:2000]
    except FileNotFoundError:
        return f"Error: file '{path}' not found. Check the path and try again."
    except Exception as e:
        return f"Error reading file: {e}"

# ---------- 3. query_sqlite ----------
def query_sqlite(query):
    try:
        conn = sqlite3.connect("test.db")
        cur = conn.cursor()
        cur.execute(query)
        rows = cur.fetchall()
        conn.close()
        return str(rows) if rows else "No rows returned."
    except Exception as e:
        return f"Error running query: {e}"

# ---------- 4. call_external_api ----------
import urllib.request
def call_external_api(endpoint, params=None):
    try:
        url = endpoint
        if params:
            query_string = "&".join(f"{k}={v}" for k, v in params.items())
            url += f"?{query_string}"
        with urllib.request.urlopen(url, timeout=5) as resp:
            return resp.read().decode()[:1000]
    except Exception as e:
        return f"Error calling API: {e}"

# ---------- 5. send_email (mock — never actually sends) ----------
def send_email(to, subject, body):
    print(f"[MOCK EMAIL] To: {to} | Subject: {subject} | Body: {body}")
    return f"Email queued to {to} (mock — not actually sent)."

# ---------- Tool schemas ----------
tools = [
    {"type": "function", "function": {
        "name": "web_search",
        "description": "Search the web for current information. Use when the user asks about something you can't answer from memory alone, like recent events or live data. NOTE: in this dev environment this tool returns MOCK/placeholder data, not real results.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "The search query"}},
            "required": ["query"]
        }
    }},
    {"type": "function", "function": {
        "name": "read_file",
        "description": "Read the text contents of a local file. Use when the user references a specific file by path.",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Path to the file"}},
            "required": ["path"]
        }
    }},
    {"type": "function", "function": {
        "name": "query_sqlite",
        "description": "Run a SQL query against the local 'test.db' SQLite database and return matching rows.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "A valid SQL query"}},
            "required": ["query"]
        }
    }},
    {"type": "function", "function": {
        "name": "call_external_api",
        "description": "Call an external HTTP API endpoint and return its raw response. Use for real-time data like weather.",
        "parameters": {
            "type": "object",
            "properties": {
                "endpoint": {"type": "string", "description": "Full URL to call"},
                "params": {"type": "object", "description": "Optional query parameters as key-value pairs"}
            },
            "required": ["endpoint"]
        }
    }},
    {"type": "function", "function": {
        "name": "send_email",
        "description": "Send an email. This is a DANGEROUS/irreversible action — only call this when the user has explicitly and clearly asked to send an email.",
        "parameters": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject line"},
                "body": {"type": "string", "description": "Email body text"}
            },
            "required": ["to", "subject", "body"]
        }
    }}
]

tool_functions = {
    "web_search": web_search,
    "read_file": read_file,
    "query_sqlite": query_sqlite,
    "call_external_api": call_external_api,
    "send_email": send_email
}

# ---------- Standalone individual tool tests ----------
def run_individual_tool_tests():
    print("=== INDIVIDUAL TOOL TESTS ===")
    print(web_search("test query"))
    print(read_file("nonexistent.txt"))
    print(query_sqlite("SELECT * FROM nonexistent_table"))  # triggers the error path
    print(call_external_api("https://api.github.com"))
    print(send_email("test@example.com", "Hi", "Hello world"))
    print()

# ---------- Multi-step agent loop ----------
def run_agent(user_input, max_iterations=10):
    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful assistant with access to tools. "
                "If a tool returns placeholder, mock, or simulated data "
                "(look for markers like '[MOCK DATA]'), you must say so "
                "explicitly in your final answer instead of inventing "
                "realistic-sounding details, sources, or statistics on top of it."
            )
        },
        {"role": "user", "content": user_input}
    ]

    for step in range(max_iterations):
        resp = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )

        msg = resp.choices[0].message
        print(f"\n--- STEP {step + 1} ---")
        print("MODEL RESPONSE:", msg)

        if not msg.tool_calls:
            print("\nFINAL ANSWER:")
            print(msg.content)
            return msg.content

        messages.append(msg)

        for call in msg.tool_calls:
            name = call.function.name
            args = json.loads(call.function.arguments)

            print(f"\nEXECUTING: {name}")
            print(f"ARGS: {args}")

            try:
                result = tool_functions[name](**args)
            except Exception as e:
                result = f"Tool error: {e}"

            print(f"RESULT: {result}")

            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": str(result)
            })

    print("Max iterations reached without a final answer.")
    return None


if __name__ == "__main__":
    run_individual_tool_tests()

    run_agent(
        "Search the web for 'agentic AI trends', then read the file 'notes.txt'."
    )