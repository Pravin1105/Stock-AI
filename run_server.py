"""CLI script to launch the Stock AI FastAPI backend server."""

import uvicorn


def main() -> None:
    print("Starting Stock AI FastAPI Backend on http://127.0.0.1:8000 ...")
    uvicorn.run(
        "src.api.app:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
    )


if __name__ == "__main__":
    main()
