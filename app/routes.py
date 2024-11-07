from flask import Blueprint, request, jsonify
from app.models import User

auth = Blueprint('auth', __name__)

@auth.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    role = data.get('role')

    # Liste des rôles valides
    roles_valides = ['administrateur', 'chef d\'équipe', 'utilisateur']

    # Vérifier si le rôle est valide
    if role not in roles_valides:
        return jsonify({"message": "Rôle non valide. Choisissez entre 'administrateur', 'chef d'équipe', ou 'utilisateur'."}), 400

    # Vérifie si l'utilisateur existe déjà
    if User.find_by_username(username):
        return jsonify({"message": "Nom d'utilisateur déjà pris."}), 400

    # Création de l'utilisateur
    User.create_user(username, password, email, role)
    return jsonify({"message": "Utilisateur enregistré avec succès."}), 201

@auth.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.find_by_username(username)
    if user and user['password'] == password:
        return jsonify({"message": "Connexion réussie."}), 200
    return jsonify({"message": "Nom d'utilisateur ou mot de passe incorrect."}), 401
