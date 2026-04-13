import ast
import operator as op

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Calculator API")
app.mount("/static", StaticFiles(directory="static"), name="static")

SAFE_OPERATORS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.Mod: op.mod,
    ast.USub: op.neg,
    ast.UAdd: op.pos,
    ast.FloorDiv: op.floordiv,
}


def evaluate_expression(node):
    if isinstance(node, ast.Expression):
        return evaluate_expression(node.body)

    if isinstance(node, ast.BinOp):
        operator = SAFE_OPERATORS.get(type(node.op))
        if operator is None:
            raise ValueError("Unsupported operator")
        return operator(
            evaluate_expression(node.left),
            evaluate_expression(node.right),
        )

    if isinstance(node, ast.UnaryOp):
        operator = SAFE_OPERATORS.get(type(node.op))
        if operator is None:
            raise ValueError("Unsupported unary operator")
        return operator(evaluate_expression(node.operand))

    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("Invalid literal")

    if isinstance(node, ast.Num):
        return node.n

    raise ValueError("Unsupported expression")


def safe_eval(expression: str):
    try:
        parsed = ast.parse(expression, mode="eval")
        return evaluate_expression(parsed)
    except (SyntaxError, ValueError, TypeError, ZeroDivisionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/", response_class=HTMLResponse)
def read_index():
    with open("static/index.html", "r", encoding="utf-8") as html_file:
        return HTMLResponse(content=html_file.read())


@app.get("/api/calc")
def calculate(expression: str = Query(..., min_length=1)):
    result = safe_eval(expression)
    return {"result": result, "expression": expression}
