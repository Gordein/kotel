from flask import Flask

from .config import Config
from .db import Base, SessionLocal, init_engine


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)

    engine = init_engine(app.config["DB_PATH"])
    from . import models  # noqa: F401  (register mappers)
    Base.metadata.create_all(engine)

    @app.teardown_appcontext
    def _remove_session(exc=None):
        SessionLocal.remove()

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    return app
