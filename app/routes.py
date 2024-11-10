from flask import Blueprint, request, jsonify
from app.models import User, Project

auth = Blueprint('auth', __name__)
project = Blueprint('project', __name__)

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
    
     # Vérifie la sécurité du mot de passe
    if not User.is_password_secure(password):
        return jsonify({"message": "Mot de passe non sécurisé. Il doit contenir au moins 8 caractères, dont des lettres, des chiffres et un caractère spécial."}), 400

    # Vérifie si l'email est valide
    if not User.is_email_valid(email):
        return jsonify({"message": "Email invalide. Entrez une adresse email correcte."}), 400

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
    if user and User.verify_password(password, user['password'].encode('utf-8')):
        return jsonify({"message": "Connexion réussie."}), 200
    return jsonify({"message": "Nom d'utilisateur ou mot de passe incorrect."}), 401

@project.route('/create', methods=['POST'])
def create_project():
    data = request.get_json()
    username = data.get('username')
    name = data.get('name')
    description = data.get('description')
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    members = data.get('members', [])
    state = data.get('state', 'en cours')

    # Vérifier les champs requis
    if not all([username, name, start_date, end_date]):
        return jsonify({"message": "Tous les champs requis doivent être fournis."}), 400

    # Créer le projet
    response, status_code = Project.create_project(name, description, start_date, end_date, state, username, members)
    return jsonify(response), status_code
