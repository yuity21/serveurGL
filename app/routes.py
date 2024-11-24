from flask import Blueprint, request, jsonify
from app.models import User, Project, Task, TaskComment, TimeTracking, Notification
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
    if status_code == 201:
        for member in members:
            Notification.add_notification(member, f"Vous avez été assigné au projet '{name}'.")
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
    for member in assigned_to:
        Notification.add_notification(member, f"Vous avez été assigné à la tâche '{task_name}' du projet '{project_name}'.")

    cursor.close()
    return jsonify({"message": "Tâche créée avec succès."}), 201

@task.route('/add_dependency', methods=['POST'])
def add_task_dependency():
        data = request.get_json()
        username = data.get('username')
        task_name_priority = data.get('task_name_priority')
        task_name_dep = data.get('task_name_dep')

        # Vérifier les champs requis
        if not all([username, task_name_priority, task_name_dep]):
            return jsonify({"message": "Tous les champs requis doivent être fournis."}), 400

        # Obtenir les tâches par leur nom
        db = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute("SELECT * FROM tasks WHERE task_name = %s", (task_name_priority,))
        task_priority = cursor.fetchone()

        cursor.execute("SELECT * FROM tasks WHERE task_name = %s", (task_name_dep,))
        task_dep = cursor.fetchone()

        if not task_priority or not task_dep:
            cursor.close()
            return jsonify({"message": "Une ou plusieurs tâches n'ont pas été trouvées."}), 404

        # Vérifier que la dépendance ne crée pas un interblocage (cercle)
        if Task.has_circular_dependency(task_priority['id'], task_dep['id']):
            cursor.close()
            return jsonify({"message": "La dépendance crée un interblocage."}), 400

        # Ajouter la dépendance
        cursor.execute(
            "INSERT INTO task_dependencies (task_id, dependent_task_id) VALUES (%s, %s)",
            (task_priority['id'], task_dep['id'])
        )
        db.commit()
        cursor.close()

        return jsonify({"message": "Dépendance ajoutée avec succès"}), 201

@task.route('/update_state', methods=['POST'])
def update_task_state():
    data = request.get_json()
    username = data.get('username')
    task_name = data.get('task_name')
    new_status = data.get('status')

    if not all([username, task_name, new_status]):
        return jsonify({"message": "Tous les champs requis doivent être fournis."}), 400

    # Vérifier les autorisations de l'utilisateur
    user = User.find_by_username(username)
    if not user:
        return jsonify({"message": "Utilisateur non trouvé."}), 404

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM tasks WHERE task_name = %s", (task_name,))
    task = cursor.fetchone()

    if not task:
        cursor.close()
        return jsonify({"message": "Tâche non trouvée."}), 404

    # Vérifier les droits d'accès
    if user['role'] not in ['administrateur', 'chef d\'équipe'] and user['username'] not in [task['created_by']]:
        cursor.execute("SELECT * FROM task_assignments WHERE task_id = %s AND username = %s", (task['id'], username))
        if not cursor.fetchone():
            cursor.close()
            return jsonify({"message": "Vous n'avez pas les droits nécessaires pour modifier cette tâche."}), 403

    # Vérifier les dépendances
    if new_status in ['en cours', 'terminée']:
        cursor.execute(
            "SELECT * FROM task_dependencies WHERE dependent_task_id = %s", (task['id'],)
        )
        dependencies = cursor.fetchall()
        for dependency in dependencies:
            cursor.execute("SELECT status FROM tasks WHERE id = %s", (dependency['task_id'],))
            dep_task = cursor.fetchone()
            if dep_task and dep_task['status'] != 'terminée':
                cursor.close()
                return jsonify({"message": "La tâche ne peut pas être mise à jour tant que ses dépendances ne sont pas terminées."}), 400

    # Mettre à jour l'état de la tâche
    cursor.execute(
        "UPDATE tasks SET status = %s WHERE id = %s",
        (new_status, task['id'])
    )
    db.commit()
    cursor.close()

    return jsonify({"message": f"L'état de la tâche '{task_name}' a été mis à jour à '{new_status}'."}), 200

@task.route('/display', methods=['POST'])
def display_tasks():
    data = request.get_json()
    username = data.get('username')
    nom_projet = data.get('nom_projet')

    # Vérifier les champs requis
    if not all([username, nom_projet]):
        return jsonify({"message": "Le nom du projet et le nom d'utilisateur sont requis."}), 400

    # Obtenir l'utilisateur
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    if not user:
        cursor.close()
        return jsonify({"message": "Utilisateur non trouvé."}), 404

    # Obtenir le projet par son nom
    cursor.execute("SELECT * FROM projects WHERE name = %s", (nom_projet,))
    projet = cursor.fetchone()
    if not projet:
        cursor.close()
        return jsonify({"message": "Projet non trouvé."}), 404

    # Obtenir les tâches selon le rôle de l'utilisateur
    tasks = []

    if user['role'] == 'administrateur':
        # Administrateur : peut voir toutes les tâches du projet
        cursor.execute("SELECT * FROM tasks WHERE project_id = %s", (projet['id'],))
        tasks = cursor.fetchall()

    elif user['role'] == 'chef d\'équipe':
        # Chef d'équipe : peut voir toutes les tâches du projet s'il en fait partie
        cursor.execute("SELECT * FROM project_members WHERE project_id = %s AND username = %s", (projet['id'], username))
        project_member = cursor.fetchone()
        if project_member:
            cursor.execute("SELECT * FROM tasks WHERE project_id = %s", (projet['id'],))
            tasks = cursor.fetchall()
        else:
            cursor.close()
            return jsonify({"message": "Vous ne faites pas partie de ce projet."}), 403

    elif user['role'] == 'utilisateur':
        # Utilisateur : peut voir uniquement les tâches qui lui sont assignées dans le projet auquel il appartient
        cursor.execute("SELECT * FROM project_members WHERE project_id = %s AND username = %s", (projet['id'], username))
        project_member = cursor.fetchone()
        if project_member:
            cursor.execute("""
                SELECT t.* FROM tasks t
                JOIN task_assignments ta ON t.id = ta.task_id
                WHERE t.project_id = %s AND ta.username = %s
            """, (projet['id'], username))
            tasks = cursor.fetchall()
        else:
            cursor.close()
            return jsonify({"message": "Vous ne faites pas partie de ce projet."}), 403

    cursor.close()
    return jsonify({"tasks": tasks}), 200

@task.route('/comment', methods=['POST'])
def add_task_comment():
    data = request.get_json()
    username = data.get('username')
    task_name = data.get('task_name')
    comment = data.get('comment')

    # Vérifier les champs requis
    if not all([username, task_name, comment]):
        return jsonify({"message": "Tous les champs requis doivent être fournis."}), 400

    # Obtenir l'utilisateur
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    if not user:
        cursor.close()
        return jsonify({"message": "Utilisateur non trouvé."}), 404

    # Obtenir la tâche
    cursor.execute("SELECT * FROM tasks WHERE task_name = %s", (task_name,))
    task = cursor.fetchone()
    if not task:
        cursor.close()
        return jsonify({"message": "Tâche non trouvée."}), 404

    # Vérifier les droits d'accès
    if user['role'] == 'administrateur':
        # L'administrateur peut commenter toutes les tâches
        pass
    elif user['role'] == 'chef d\'équipe':
        # Le chef d'équipe peut commenter toutes les tâches du projet s'il en fait partie
        cursor.execute("SELECT * FROM project_members WHERE project_id = %s AND username = %s", (task['project_id'], username))
        if not cursor.fetchone():
            cursor.close()
            return jsonify({"message": "Vous ne faites pas partie de ce projet."}), 403
    elif user['role'] == 'utilisateur':
        # L'utilisateur peut seulement commenter les tâches auxquelles il est assigné
        cursor.execute("SELECT * FROM task_assignments WHERE task_id = %s AND username = %s", (task['id'], username))
        if not cursor.fetchone():
            cursor.close()
            return jsonify({"message": "Vous n'avez pas le droit de commenter cette tâche."}), 403

    # Ajouter le commentaire
    response, status_code = TaskComment.add_comment(task['id'], username, comment)
    if status_code == 201:
        # Ajouter des notifications pour les membres assignés à la tâche
        cursor.execute("SELECT username FROM task_assignments WHERE task_id = %s", (task['id'],))
        assigned_users = cursor.fetchall()
        for assigned_user in assigned_users:
            Notification.add_notification(assigned_user['username'], f"Un nouveau commentaire a été ajouté à la tâche '{task_name}'.")
    cursor.close()
    return jsonify(response), status_code

@task.route('/time/track', methods=['POST'])
def track_time():
    data = request.get_json()

    username = data.get('username')
    task_name = data.get('task_name')
    start_time_str = data.get('start_time')
    end_time_str = data.get('end_time')

    # Vérification des données fournies
    if not all([username, task_name, start_time_str, end_time_str]):
        return jsonify({"message": "Données manquantes"}), 400

    # Conversion des chaînes de caractères en objets datetime
    try:
        start_time = datetime.fromisoformat(start_time_str)
        end_time = datetime.fromisoformat(end_time_str)
    except ValueError:
        return jsonify({"message": "Format de date invalide. Utilisez un format ISO-8601."}), 400

    # Vérification que l'heure de fin est postérieure à l'heure de début
    if end_time <= start_time:
        return jsonify({"message": "L'heure de fin doit être postérieure à l'heure de début."}), 400

    # Vérifier si la tâche existe
    cursor = get_db().cursor()
    cursor.execute("SELECT id FROM tasks WHERE task_name = %s", (task_name,))
    task = cursor.fetchone()

    if not task:
        return jsonify({"message": "Tâche non trouvée."}), 404

    # Vérification que l'utilisateur est assigné à la tâche ou possède le droit de la modifier
    cursor.execute("""
        SELECT username 
        FROM task_assignments 
        WHERE task_id = %s AND username = %s
    """, (task[0], username))
    assigned_user = cursor.fetchone()

    cursor.execute("""
        SELECT role 
        FROM users 
        WHERE username = %s
    """, (username,))
    user = cursor.fetchone()

    if not assigned_user and (not user or user[0] not in ['administrateur']):
        return jsonify({"message": "Vous n'avez pas accès à cette tâche."}), 403

    # Enregistrer le suivi du temps dans la table `time_entries`
    cursor.execute("""
        INSERT INTO time_entries (task_id, username, start_time, end_time)
        VALUES (%s, %s, %s, %s)
    """, (task[0], username, start_time, end_time))
    get_db().commit()
    cursor.close()

    return jsonify({"message": "Temps enregistré avec succès"}), 201


@project.route('/report/time', methods=['POST'])
def time_report():
    data = request.get_json()
    username = data.get('username')
    project_name = data.get('project_name')

    # Vérifier les champs requis
    if not all([username, project_name]):
        return jsonify({"message": "Tous les champs requis doivent être fournis."}), 400

    # Vérifier l'utilisateur
    user = User.find_by_username(username)
    if not user:
        return jsonify({"message": "Utilisateur non trouvé."}), 404

    # Vérifier le projet
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM projects WHERE name = %s", (project_name,))
    project = cursor.fetchone()

    if not project:
        cursor.close()
        return jsonify({"message": "Projet non trouvé."}), 404

    # Vérifier si l'utilisateur a accès au projet
    if user['role'] != 'administrateur':
        cursor.execute("SELECT * FROM project_members WHERE project_id = %s AND username = %s", (project['id'], username))
        if not cursor.fetchone():
            cursor.close()
            return jsonify({"message": "Vous ne faites pas partie de ce projet."}), 403

    # Obtenir les entrées de temps
    time_entries = TimeTracking.get_time_entries(project_id=project['id'])
    cursor.close()

    # Calculer le temps total
    total_time = sum(entry['duration_minutes'] for entry in time_entries)

    return jsonify({
        "project": project_name,
        "total_time_minutes": total_time,
        "time_entries": time_entries
    }), 200

@auth.route('/notifications', methods=['POST'])
def get_notifications():
    data = request.get_json()
    username = data.get('username')

    # Vérifier si l'utilisateur existe
    user = User.find_by_username(username)
    if not user:
        return jsonify({"message": "Utilisateur non trouvé."}), 404

    # Obtenir les notifications
    notifications = Notification.get_notifications(username)
    return jsonify({"notifications": notifications}), 200

@auth.route('/notifications/read', methods=['POST'])
def mark_notification_as_read():
    data = request.get_json()
    notification_id = data.get('notification_id')

    # Marquer la notification comme lue
    Notification.mark_as_read(notification_id)
    return jsonify({"message": "Notification marquée comme lue."}), 200
