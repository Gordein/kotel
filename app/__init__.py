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

    from .cli import init_db
    app.cli.add_command(init_db)

    from .auth import current_user as _current_user
    from .views.auth_views import bp as auth_bp
    from .views.balance_views import bp as balance_bp
    from .views.expense_views import bp as expense_bp
    from .views.feed_views import bp as feed_bp
    from .views.profile_views import bp as profile_bp
    from .views.settlement_views import bp as settlement_bp
    for blueprint in (auth_bp, balance_bp, expense_bp, feed_bp, profile_bp, settlement_bp):
        app.register_blueprint(blueprint)

    @app.context_processor
    def _inject_user():
        return {"current_user": _current_user()}

    return app
