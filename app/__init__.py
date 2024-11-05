from flask import Flask
from app.config import Config
from app.routes import auth
from app.db import close_db

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Enregistrement du blueprint
    app.register_blueprint(auth, url_prefix='/auth')

    # Ferme la connexion à la base de données après chaque requête
    app.teardown_appcontext(close_db)

    return app

