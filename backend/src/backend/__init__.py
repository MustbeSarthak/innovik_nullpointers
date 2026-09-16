"""Healthcare Assistant backend package.

The console entry point (``backend``) starts the FastAPI application with
uvicorn so the survey API can be exercised locally.
"""


def main() -> None:
    """Run the Healthcare Assistant API with uvicorn."""
    import uvicorn

    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=False)
