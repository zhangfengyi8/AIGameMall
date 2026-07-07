import os

import uvicorn


def build_server_config() -> uvicorn.Config:
    host = os.getenv("AIGAMEMALL_API_HOST", "0.0.0.0")
    port = int(os.getenv("AIGAMEMALL_API_PORT", "8000"))
    reload = os.getenv("AIGAMEMALL_API_RELOAD", "false").lower() in {"1", "true", "yes"}
    return uvicorn.Config("app.main:app", host=host, port=port, reload=reload)


def main() -> None:
    server = uvicorn.Server(build_server_config())
    server.run()


if __name__ == "__main__":
    main()
