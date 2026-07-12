import os

from fastapi import FastAPI

VERSION = "0.1.0"


def create_app(db_path: str | None = None, standards_dir: str | None = None) -> FastAPI:
    db_path = db_path or os.environ.get("DB_PATH", "/data/inspections.db")
    standards_dir = standards_dir or os.path.join(os.path.dirname(__file__), "standards")

    app = FastAPI(title="container-inspect", version=VERSION)
    app.state.db_path = db_path
    app.state.standards_dir = standards_dir

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "container-inspect", "version": VERSION}

    return app


app = create_app()
