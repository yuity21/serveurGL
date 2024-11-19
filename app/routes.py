from flask import Blueprint, request, jsonify
from app.models import User, Project, Task
from app.db import get_db
from datetime import datetime

auth = Blueprint('auth', __name__)
project = Blueprint('project', __name__)
task = Blueprint('task', __name__)

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

@project.route('/update_state', methods=['POST'])
def update_project_state():
    data = request.get_json()
    username = data.get('username')
    project_name = data.get('project_name')

    # Vérifie si l'utilisateur existe et s'il est autorisé
    user = User.find_by_username(username)
    if not user:
        return jsonify({"message": "Utilisateur non trouvé."}), 404

    if user['role'] not in ['administrateur', 'chef d\'équipe']:
        return jsonify({"message": "Vous n'avez pas l'autorisation de modifier l'état du projet."}), 403

    # Met à jour l'état du projet si l'utilisateur est autorisé
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM projects WHERE name = %s", (project_name,))
    project = cursor.fetchone()

    if not project:
        cursor.close()
        return jsonify({"message": "Projet non trouvé."}), 404

    if project['state'] == 'terminé':
        cursor.close()
        return jsonify({"message": "Le projet est déjà terminé."}), 400

    cursor.execute(
        "UPDATE projects SET state = 'terminé' WHERE name = %s",
        (project_name,)
    )
    db.commit()
    cursor.close()

    return jsonify({"message": f"L'état du projet '{project_name}' a été modifié à 'terminé'."}), 200

@project.route('/display', methods=['POST'])
def display_data():
    data = request.get_json()
    username = data.get('username')

    # Vérifie si l'utilisateur existe
    user = User.find_by_username(username)
    if not user:
        return jsonify({"message": "Utilisateur non trouvé."}), 404

    # Récupère l'action demandée (liste des utilisateurs ou projets de l'utilisateur)
    display_type = data.get('display_type')

    db = get_db()
    cursor = db.cursor(dictionary=True)

    if display_type == 'users':
        # Affiche la liste de tous les utilisateurs
        cursor.execute("SELECT username, email, role, created_at FROM users")
        users = cursor.fetchall()
        cursor.close()
        return jsonify({"users": users}), 200

    elif display_type == 'projects':
        if user['role'] == 'administrateur':
            # Si l'utilisateur est un administrateur, afficher tous les projets
            cursor.execute("SELECT * FROM projects")
        else:
            # Sinon, afficher les projets auxquels il appartient
            cursor.execute("""
                SELECT p.id, p.name, p.description, p.start_date, p.end_date, p.state, p.created_by
                FROM projects p
                JOIN project_members pm ON p.id = pm.project_id
                WHERE pm.username = %s
            """, (username,))
        
        projects = cursor.fetchall()
        cursor.close()
        return jsonify({"projects": projects}), 200

    else:
        # Si le type de données à afficher n'est pas spécifié ou incorrect
        cursor.close()
        return jsonify({"message": "Type d'affichage non valide. Utilisez 'users' ou 'projects'."}), 400

@task.route('/create', methods=['POST'])
def create_task():
    data = request.get_json()
    username = data.get('username')
    project_name = data.get('nom_projet')
    task_name = data.get('task_name')
    description = data.get('description', '')
    assigned_to = data.get('assigned_to', [])
    priority = data.get('priority', 'moyenne')
    status = data.get('status', 'A faire')
    due_date = data.get('date_echeance')

    # Vérifier les champs requis
    if not all([username, project_name, task_name, priority, due_date]):
        return jsonify({"message": "Tous les champs requis doivent être fournis."}), 400

    # Vérifier si l'utilisateur existe et est autorisé à créer la tâche
    user = User.find_by_username(username)
    if not user:
        return jsonify({"message": "Utilisateur non trouvé."}), 404

    if user['role'] not in ['administrateur', 'chef d\'équipe']:
        return jsonify({"message": "Vous n'avez pas l'autorisation de créer une tâche."}), 403

    # Vérifier si le projet existe
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM projects WHERE name = %s", (project_name,))
    project = cursor.fetchone()

    if not project:
        cursor.close()
        return jsonify({"message": "Projet non trouvé."}), 404

    # Vérifier si l'utilisateur est un chef d'équipe du projet ou un administrateur
    if user['role'] != 'administrateur':
        cursor.execute("SELECT * FROM project_members WHERE project_id = %s AND username = %s", (project['id'], username))
        member = cursor.fetchone()
        if not member:
            cursor.close()
            return jsonify({"message": "Vous devez faire partie du projet pour créer une tâche."}), 403

    # Vérifier que les membres assignés font partie du projet
    invalid_members = [member for member in assigned_to if not User.find_by_username(member)]
    if invalid_members:
        cursor.close()
        return jsonify({"message": f"Les utilisateurs suivants n'existent pas : {', '.join(invalid_members)}"}), 400

    for member in assigned_to:
        cursor.execute("SELECT * FROM project_members WHERE project_id = %s AND username = %s", (project['id'], member))
        if not cursor.fetchone():
            cursor.close()
            return jsonify({"message": f"L'utilisateur {member} ne fait pas partie du projet."}), 400

    # Convertir la date d'échéance (str) en objet datetime.date
    try:
        due_date_obj = datetime.strptime(due_date, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"message": "Le format de la date d'échéance est incorrect. Utilisez AAAA-MM-JJ."}), 400
    # Vérifier que la date d'échéance est valide
    if due_date_obj > project['end_date']:
        cursor.close()
        return jsonify({"message": "La date d'échéance ne peut pas dépasser la date de fin du projet."}), 400

    # Créer la tâche
    task_id = Task.create_task(project['id'], task_name, description, priority, status, due_date, username)

    # Ajouter les membres assignés à la tâche
    Task.assign_members(task_id, assigned_to)

    cursor.close()
    return jsonify({"message": "Tâche créée avec succès."}), 201
