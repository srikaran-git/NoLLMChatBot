"""Interactive Jev-routed tools using KodeKloud's OpenAI-compatible API."""

import asyncio
import ast
import json
import os
import re
import sys
from pathlib import Path

import calculator
import weather
import web_search
from dotenv import load_dotenv
from openai import AsyncOpenAI


PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_BASE_URL = "https://api.ai.kodekloud.com/v1"
DEFAULT_MODEL = "typesafe/jev-1.13.0"
JEV_TOOL_RESPONSE_FORMAT = {
    "type": "questions",
    "questions": {
        "tool": {
            "type": "choice",
            "instructions": (
                "Which one tool is needed to fulfil the user's request? "
                "Choose unsupported when none applies."
            ),
            "criteria": {
                "calculator": "Arithmetic or a numerical calculation.",
                "weather": "Current weather or forecast for a location.",
                "web_search": "Find information on the public web.",
                "unsupported": "Anything that cannot be fulfilled by the listed tools.",
            },
        }
    },
}

TOOL_NAMES = {"calculator", "weather", "web_search", "unsupported"}



def create_client() -> AsyncOpenAI:
    """Create a minimal client compatible with Jev's chat-completions route."""
    api_key = os.getenv("API_KEY") or os.getenv("KODEKEY_API_KEY")
    if not api_key:
        raise RuntimeError(
            "API_KEY is not set. Copy .env.example to .env and add your KodeKey."
        )

    return AsyncOpenAI(
        api_key=api_key,
        base_url=os.getenv("BASE_URL", DEFAULT_BASE_URL),
    )


def extract_tool_choice(content: str) -> str:
    """Extract Jev's chosen tool from its JSON response."""
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        payload = content

    def find_choice(value: object) -> str | None:
        if isinstance(value, str):
            candidate = value.lower().strip()
            return candidate if candidate in TOOL_NAMES else None
        if isinstance(value, dict):
            choice = value.get("choice")
            if isinstance(choice, str) and choice in TOOL_NAMES:
                return choice
            for nested in value.values():
                found = find_choice(nested)
                if found:
                    return found
        if isinstance(value, list):
            for nested in value:
                found = find_choice(nested)
                if found:
                    return found
        return None

    choice = find_choice(payload)
    if not choice:
        raise ValueError(f"Could not read a tool choice from Jev's response: {content}")
    return choice


def extract_math_expression(prompt: str) -> str:
    candidates = re.findall(r"[0-9.()\s+*/-]+", prompt)
    expression = max(
        (item.strip() for item in candidates if re.search(r"\d", item)),
        default="",
        key=len,
    )
    if not expression:
        raise ValueError("Include a numeric expression, for example: what is (3 + 5) * 12?")
    return expression


def calculate(expression: str) -> int | float:
    """Evaluate basic arithmetic through the bundled calculator tools only."""
    def evaluate(node: ast.expr) -> int | float:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp):
            left, right = evaluate(node.left), evaluate(node.right)
            if isinstance(node.op, ast.Add):
                return calculator.add(left, right)
            if isinstance(node.op, ast.Sub):
                return calculator.subtract(left, right)
            if isinstance(node.op, ast.Mult):
                return calculator.multiply(left, right)
            if isinstance(node.op, ast.Div):
                return calculator.divide(left, right)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -evaluate(node.operand)
        raise ValueError("Only numbers, parentheses, +, -, *, and / are supported")

    return evaluate(ast.parse(expression, mode="eval").body)


def extract_location(prompt: str) -> str:
    match = re.search(r"(?:weather|forecast|temperature)(?:\s+(?:in|for|at))?\s+(.+?)\??$", prompt, re.I)
    if not match:
        raise ValueError("Say the location, for example: weather in Mumbai")
    return match.group(1).strip()


def extract_search_query(prompt: str) -> str:
    match = re.search(r"(?:search(?:\s+for)?|look up|google)\s+(.+)$", prompt, re.I)
    if not match:
        raise ValueError("Start the request with search, for example: search current Python release")
    return match.group(1).strip()


async def choose_tool(client: AsyncOpenAI, model: str, prompt: str) -> str:
    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        extra_body={"response_format": JEV_TOOL_RESPONSE_FORMAT},
    )
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError(f"Jev returned no tool choice: {response.model_dump_json()}")
    return extract_tool_choice(content)


async def run_tool(tool_name: str, prompt: str) -> object:
    if tool_name == "calculator":
        return calculate(extract_math_expression(prompt))
    if tool_name == "weather":
        return await weather.weather(extract_location(prompt))
    if tool_name == "web_search":
        return await web_search.web_search(extract_search_query(prompt))
    return "I can calculate arithmetic, get weather, or search the web."


async def main() -> None:
    load_dotenv(PROJECT_DIR / ".env")
    client = create_client()
    model = os.getenv("MODEL", DEFAULT_MODEL)
    print("Jev tool router ready. Ask for arithmetic, weather, or a web search.")
    print("Examples: what is 2 + 5? | weather in Mumbai | search Python 3.14 release")

    try:
        while True:
            try:
                prompt = (await asyncio.to_thread(input, "> ")).strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if prompt.lower() in {"quit", "exit"}:
                break
            if not prompt:
                continue

            try:
                tool_name = await choose_tool(client, model, prompt)
                print(json.dumps(await run_tool(tool_name, prompt), indent=2))
            except Exception as exc:
                print(f"Request failed: {exc}", file=sys.stderr)
    finally:
        await client.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError as exc:
        print(f"Startup failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
