from flask import Flask
from .routes import bp
from .providers import get_all_providers

def create_app(cache_enabled: bool):
    app = Flask(__name__)
    
    app.secret_key = "super-secret-key"

    app.config.from_object("config.Config")
    app.config["CACHE_ENABLED"] = cache_enabled
    app.config["HEADERS"] = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        )
    }
    app.config["BASE_URL"] = "https://www.examtopics.com"

    if not app.config["CACHE_ENABLED"]:
        app.config["PROVIDERS"] = get_all_providers(base_url=app.config["BASE_URL"], headers=app.config["HEADERS"])
        app.config["PROVIDERS"] = dict(
            sorted(
                (k, v) for k, v in app.config["PROVIDERS"].items() if k != "exams" # sort and remove all exams entry
            )
        )

    else: #todo
        pass
    
    app.register_blueprint(bp)
    return app
