from flask import Blueprint, request, jsonify
from app.models import User, Project, Task, TaskComment, TimeTracking, Notification
from app.db import get_db
from datetime import datetime

auth = Blueprint('auth', __name__)
project = Blueprint('project', __name__)
task = Blueprint('task', __name__)
user = Blueprint('user',__name__)

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

@task.route('/get_assigned_users', methods=['POST'])
def get_assigned_users():
    data = request.get_json()
    entity_type = data.get('type')  # "project" ou "task"
    entity_name = data.get('name')

    # Validation des champs
    if not all([entity_type, entity_name]):
        return jsonify({"message": "Le type et le nom sont requis."}), 400

    # Validation du type
    if entity_type not in ["project", "task"]:
        return jsonify({"message": "Type invalide. Utilisez 'project' ou 'task'."}), 400

    try:
        if entity_type == "project":
            users = Project.get_assigned_users(entity_name)
        else:  # entity_type == "task"
            users = Task.get_assigned_users(entity_name)

        if not users:
            return jsonify({"message": f"Aucun utilisateur trouvé pour le {entity_type} '{entity_name}'."}), 404

        return jsonify({"users": users}), 200

    except Exception as e:
        return jsonify({"message": f"Erreur : {str(e)}"}), 500
    
@user.route('/change_role', methods=['POST'])
def change_role():
    data = request.get_json()

    # Vérifiez que le JSON contient tous les champs nécessaires
    if not all(key in data for key in ['admin_username', 'target_username', 'new_role']):
        return jsonify({"error": "Requête invalide. Champs requis : admin_username, target_username, new_role"}), 400

    admin_username = data['admin_username']
    target_username = data['target_username']
    new_role = data['new_role']

    # Vérifiez que le rôle demandé est valide
    valid_roles = ['utilisateur', 'chef d\'équipe']
    if new_role not in valid_roles:
        return jsonify({"error": f"Rôle invalide. Rôles possibles : {', '.join(valid_roles)}"}), 400

    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)

        # Vérifiez que l'utilisateur qui effectue la demande est un administrateur
        cursor.execute("SELECT role FROM users WHERE username = %s", (admin_username,))
        admin = cursor.fetchone()
        if not admin or admin['role'] != 'administrateur':
            return jsonify({"error": "Seuls les administrateurs peuvent changer les rôles."}), 403

        # Vérifiez que l'utilisateur cible existe et n'est pas administrateur
        cursor.execute("SELECT username, role FROM users WHERE username = %s", (target_username,))
        target_user = cursor.fetchone()
        if not target_user:
            return jsonify({"error": f"L'utilisateur '{target_username}' n'existe pas."}), 404
        if target_user['role'] == 'administrateur':
            return jsonify({"error": "Vous ne pouvez pas changer le rôle d'un administrateur."}), 403

        # Vérifiez si le rôle demandé est déjà celui de l'utilisateur
        if target_user['role'] == new_role:
            return jsonify({"error": f"L'utilisateur '{target_username}' a déjà le rôle '{new_role}'."}), 400

        # Mettez à jour le rôle de l'utilisateur cible
        cursor.execute(
            "UPDATE users SET role = %s WHERE username = %s",
            (new_role, target_username)
        )
        conn.commit()

    return jsonify({"message": f"Le rôle de '{target_username}' a été changé en '{new_role}' avec succès."}), 200

@task.route('/comments', methods=['POST'])
def get_task_comments():
    data = request.get_json()
    username = data.get('username')
    task_name = data.get('task_name')

    # Vérification des champs requis
    if not all([username, task_name]):
        return jsonify({"message": "Le nom d'utilisateur et le nom de la tâche sont requis."}), 400

    # Vérification que l'utilisateur existe
    user = User.find_by_username(username)
    if not user:
        return jsonify({"message": "Utilisateur non trouvé."}), 404

    # Vérification que la tâche existe
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM tasks WHERE task_name = %s", (task_name,))
    task = cursor.fetchone()
    if not task:
        cursor.close()
        return jsonify({"message": "Tâche non trouvée."}), 404

    # Obtenir les commentaires de la tâche
    comments = TaskComment.get_task_comments_with_details(task_name)
    if not comments:
        return jsonify({"message": "Aucun commentaire trouvé pour cette tâche."}), 404

    return jsonify({"comments": comments}), 200

@task.route('/dependencies', methods=['POST'])
def get_task_dependencies():
    data = request.get_json()

    # Vérifiez si toutes les données nécessaires sont fournies
    if not data or 'username' not in data or 'task_name' not in data:
        return jsonify({"message": "Données invalides. Veuillez fournir 'username' et 'task_name'."}), 400

    username = data['username']
    task_name = data['task_name']

    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        # Vérifiez si l'utilisateur existe
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        if not user:
            return jsonify({"message": "Utilisateur introuvable."}), 404

        # Vérifiez si la tâche existe
        cursor.execute("SELECT * FROM tasks WHERE task_name = %s", (task_name,))
        task = cursor.fetchone()
        if not task:
            return jsonify({"message": f"La tâche '{task_name}' est introuvable."}), 404

        # Récupérez les dépendances de la tâche
        cursor.execute("""
            SELECT t.task_name
            FROM tasks t
            JOIN task_dependencies td ON t.id = td.task_id
            WHERE td.dependent_task_id = %s
        """, (task['id'],))
        dependencies = cursor.fetchall()

        if not dependencies:
            return jsonify({"message": f"La tâche '{task_name}' n'a pas de dépendances."}), 200

        # Liste les noms des tâches dépendantes
        dependency_names = [d['task_name'] for d in dependencies]
        return jsonify({"message": f"Les tâches suivantes doivent être terminées avant de commencer '{task_name}' : {', '.join(dependency_names)}"}), 200

    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500

    finally:
        cursor.close()

@task.route('/time_tracking', methods=['POST'])
def get_user_time_tracking():
    data = request.get_json()
    username = data.get('username')

    # Vérification des champs requis
    if not username:
        return jsonify({"message": "Le nom d'utilisateur est requis."}), 400

    # Vérification que l'utilisateur existe
    user = User.find_by_username(username)
    if not user:
        return jsonify({"message": "Utilisateur non trouvé."}), 404

    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        # Obtenez les entrées de time tracking pour cet utilisateur
        cursor.execute("""
            SELECT te.start_time, te.end_time, te.duration_minutes, t.task_name
            FROM time_entries te
            JOIN tasks t ON te.task_id = t.id
            WHERE te.username = %s
            ORDER BY te.start_time ASC
        """, (username,))
        time_entries = cursor.fetchall()

        cursor.close()

        if not time_entries:
            return jsonify({"message": "Aucune entrée de suivi de temps trouvée pour cet utilisateur."}), 404

        return jsonify({"time_tracking": time_entries}), 200

    except Exception as e:
        return jsonify({"message": f"Erreur serveur : {str(e)}"}), 500




