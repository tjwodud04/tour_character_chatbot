"""Flask 애플리케이션 진입점 (Vercel `@vercel/python` 대상)."""

from flask import Flask

from scripts.config import DEV_SERVER_PORT
from scripts.routes import register_routes

app = Flask(
    __name__,
    static_folder="../front",
    static_url_path="",
    template_folder="../front",
)

register_routes(app)

if __name__ == "__main__":
    app.run(port=DEV_SERVER_PORT, debug=True)
