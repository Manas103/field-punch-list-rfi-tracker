"""uvicorn entry point: `python -m app.main` serves the API on :8000."""

import uvicorn


def run():
    uvicorn.run("app.api:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    run()
