import ast
import operator
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("local_utility_server")
_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}


def _calculate(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _calculate(node.operand)
        return value if isinstance(node.op, ast.UAdd) else -value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPERATORS:
        return _OPERATORS[type(node.op)](_calculate(node.left), _calculate(node.right))
    raise ValueError("Only numeric arithmetic expressions are supported")


@mcp.tool()
def calculator(expression: str) -> str:
    """Safely evaluate a basic numeric arithmetic expression."""
    tree = ast.parse(expression, mode="eval")
    return str(_calculate(tree.body))


@mcp.tool()
def current_time() -> str:
    """Return the current UTC date and time in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


@mcp.tool()
def text_length(text: str) -> str:
    """Return the number of characters in text."""
    return str(len(text))


if __name__ == "__main__":
    mcp.run(transport="stdio")
