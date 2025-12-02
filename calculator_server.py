#!/usr/bin/env python3
"""
MCP Server for Calculator with History
"""

import math
import asyncio
import datetime
import sys
from typing import List, Dict, Any
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.shared.exceptions import McpError
import mcp.types as types

# Create server instance
calc_server = Server("calculator-server")

# Store calculation history
calculation_history: List[Dict[str, Any]] = []


def safe_eval(expression: str) -> float:
    """
    Safely evaluate mathematical expressions
    """
    # Allowed functions and constants
    safe_dict = {
        'abs': abs,
        'round': round,
        'min': min,
        'max': max,
        'pow': pow,
        'sqrt': math.sqrt,
        'sin': math.sin,
        'cos': math.cos,
        'tan': math.tan,
        'asin': math.asin,
        'acos': math.acos,
        'atan': math.atan,
        'log': math.log,
        'log10': math.log10,
        'exp': math.exp,
        'pi': math.pi,
        'e': math.e
    }

    try:
        # Create a safe environment for eval
        eval_globals = {"__builtins__": {}}
        eval_globals.update(safe_dict)

        # Basic validation
        allowed_chars = set('0123456789+-*/(). sqrtabsroundminmaxpowsincostanlogexplasinacosatan')
        clean_expr = expression.replace(' ', '')

        for char in clean_expr:
            if char not in allowed_chars:
                raise ValueError(f"Invalid character in expression: {char}")

        result = eval(expression, eval_globals, {})
        return float(result)
    except Exception as e:
        raise ValueError(f"Error evaluating expression: {str(e)}")


@calc_server.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    """List available calculator tools"""
    return [
        types.Tool(
            name="calculate",
            description="Perform mathematical calculations. Supports: +, -, *, /, (), sqrt, sin, cos, tan, log, exp, pi, e",
            inputSchema={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression to evaluate"
                    }
                },
                "required": ["expression"]
            }
        ),
        types.Tool(
            name="get_history",
            description="Get calculation history with timestamps",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "number",
                        "description": "Number of recent calculations to show (default: 10)",
                        "default": 10
                    }
                }
            }
        ),
        types.Tool(
            name="clear_history",
            description="Clear calculation history",
            inputSchema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="advanced_calculate",
            description="Perform advanced mathematical operations",
            inputSchema={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["factorial", "power", "logarithm"],
                        "description": "Type of advanced operation"
                    },
                    "number": {
                        "type": "number",
                        "description": "Number for the operation"
                    },
                    "base": {
                        "type": "number",
                        "description": "Base for logarithm (default: 10)",
                        "default": 10
                    },
                    "exponent": {
                        "type": "number",
                        "description": "Exponent for power operation",
                        "default": 2
                    }
                },
                "required": ["operation", "number"]
            }
        )
    ]


@calc_server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> List[types.TextContent]:
    """Handle tool execution"""

    if name == "calculate":
        try:
            expression = arguments["expression"]
            result = safe_eval(expression)

            # Add to history
            calculation_history.append({
                "timestamp": datetime.datetime.now().isoformat(),
                "expression": expression,
                "result": result
            })

            return [types.TextContent(
                type="text",
                text=f"✅ Result: {expression} = {result}"
            )]

        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"❌ Error: {str(e)}\n\nTip: Use operators like +, -, *, /, and functions like sqrt(25), sin(pi/2)"
            )]

    elif name == "get_history":
        limit = arguments.get("limit", 10)
        recent_history = calculation_history[-limit:] if calculation_history else []

        if not recent_history:
            return [types.TextContent(type="text", text="📝 No calculations in history")]

        history_text = "📝 Calculation History\n\n"
        for i, calc in enumerate(recent_history, 1):
            history_text += f"{i}. {calc['expression']} = {calc['result']}\n"
            history_text += f"   Time: {calc['timestamp'][:19]}\n\n"

        return [types.TextContent(type="text", text=history_text)]

    elif name == "clear_history":
        calculation_history.clear()
        return [types.TextContent(type="text", text="🗑️ History cleared")]

    elif name == "advanced_calculate":
        try:
            operation = arguments["operation"]
            number = arguments["number"]
            result = None

            if operation == "factorial":
                if number < 0 or number != int(number):
                    raise ValueError("Factorial requires non-negative integer")
                result = math.factorial(int(number))

            elif operation == "power":
                exponent = arguments.get("exponent", 2)
                result = math.pow(number, exponent)

            elif operation == "logarithm":
                base = arguments.get("base", 10)
                if base == 10:
                    result = math.log10(number)
                elif base == math.e:
                    result = math.log(number)
                else:
                    result = math.log(number, base)

            # Add to history
            calc_info = f"{operation}({number}"
            if operation == "power":
                calc_info += f", {arguments.get('exponent', 2)}"
            elif operation == "logarithm":
                calc_info += f", base={arguments.get('base', 10)}"
            calc_info += ")"

            calculation_history.append({
                "timestamp": datetime.datetime.now().isoformat(),
                "expression": calc_info,
                "result": result
            })

            return [types.TextContent(
                type="text",
                text=f"✅ Result: {calc_info} = {result}"
            )]

        except Exception as e:
            return [types.TextContent(type="text", text=f"❌ Error: {str(e)}")]

    return [types.TextContent(type="text", text=f"❓ Unknown tool: {name}")]


@calc_server.list_resources()
async def handle_list_resources() -> List[types.Resource]:
    """List available resources"""
    return [
        types.Resource(
            uri="calculator://help",
            name="Calculator Help",
            description="Instructions for using the calculator",
            mimeType="text/plain"
        ),
        types.Resource(
            uri="calculator://constants",
            name="Mathematical Constants",
            description="Common mathematical constants",
            mimeType="text/plain"
        )
    ]


@calc_server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """Read resource content"""
    if uri == "calculator://help":
        return """Calculator MCP Server Help

Available Operations:
• Basic: +, -, *, /, ()
• Functions: sqrt(x), sin(x), cos(x), tan(x), asin(x), acos(x), atan(x)
• Logarithms: log(x) (natural), log10(x) (base 10)
• Exponents: exp(x), pow(x, y)
• Constants: pi, e

Examples:
• 2 + 3 * 4
• sqrt(16) + sin(pi/2)
• (5 + 3) * 2 / 4

Advanced Operations:
• Factorial: n!
• Power: x^y
• Logarithm: logₐ(x)
"""
    elif uri == "calculator://constants":
        return """Mathematical Constants

π (pi) = 3.141592653589793
  • Circumference to diameter ratio
  • Use in trigonometry: sin(pi/2) = 1

e = 2.718281828459045
  • Base of natural logarithm
  • Euler's number

Common Values:
• sqrt(2) ≈ 1.41421356
• sqrt(3) ≈ 1.73205081
• φ (golden ratio) ≈ 1.61803399
"""
    return "Resource not found"


async def main():
    """Run the server"""
    print("🚀 Starting Calculator MCP Server...", file=sys.stderr)

    # Get standard input/output streams
    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer

    try:
        # Get capabilities
        capabilities = calc_server.get_capabilities()

        # Run the server
        await calc_server.run(
            stdin,
            stdout,
            InitializationOptions(
                server_name="calculator-server",
                server_version="1.0.0",
                capabilities=capabilities
            )
        )
    except Exception as e:
        print(f"❌ Server error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
