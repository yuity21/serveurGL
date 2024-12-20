from flask import Flask,jsonify
from app.config import Config
from flask_cors import CORS
from app.routes import auth
from app.db import close_db
from app.routes import project, task, user

def create_app():
    app = Flask(__name__)
    CORS(app)
    app.config.from_object(Config)

    # Enregistrement du blueprint
    app.register_blueprint(auth, url_prefix='/auth')
    app.register_blueprint(project, url_prefix='/project')
    app.register_blueprint(task, url_prefix='/task')
    app.register_blueprint(user, url_prefix='/user')

    # Ferme la connexion à la base de données après chaque requête
    app.teardown_appcontext(close_db)

    # Gestion des erreurs liées à la base de données
    @app.errorhandler(ConnectionError)
    def handle_db_connection_error(e):
        response = jsonify({"message": str(e)})
        response.status_code = 500  # Code HTTP pour erreur serveur
        return response

    return app

