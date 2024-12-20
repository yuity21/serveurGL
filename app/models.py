import re
import bcrypt
from app.db import get_db

class User:
    def __init__(self, username, password, email, role):
        self.username = username
        self.password = password
        self.email = email
        self.role = role

    @staticmethod
    def hash_password(password):
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt)

    @staticmethod
    def verify_password(plain_password, hashed_password):
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password)

    @staticmethod
    def is_password_secure(password):
        # Mot de passe doit être de 8 caractères minimum, avec lettres, chiffres et caractères spéciaux
        return len(password) >= 8 and \
               re.search(r"[A-Za-z]", password) and \
               re.search(r"[0-9]", password) and \
               re.search(r"[!@#$%^&*()_+]", password)

    @staticmethod
    def is_email_valid(email):
        # Vérifie si l'email est dans un format valide
        return re.match(r"[^@]+@[^@]+\.[^@]+", email)

    @staticmethod
    def create_user(username, password, email, role):
        db = get_db()
        cursor = db.cursor()
        hashed_password = User.hash_password(password)
        cursor.execute(
            "INSERT INTO users (username, password, email, role) VALUES (%s, %s, %s, %s)",
            (username, hashed_password, email, role)
        )
        db.commit()
        cursor.close()

    @staticmethod
    def find_by_username(username):
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        return user
    
class Project:
    def __init__(self, name, description, start_date, end_date, state, created_by):
        self.name = name
        self.description = description
        self.start_date = start_date
        self.end_date = end_date
        self.state = state
        self.created_by = created_by

    @staticmethod
    def create_project(name, description, start_date, end_date, state, created_by, members):
        db = get_db()
        cursor = db.cursor()

        # Vérifier si le créateur du projet est un administrateur ou un chef d'équipe
        creator = User.find_by_username(created_by)
        if not creator or creator['role'] not in ['administrateur', 'chef d\'équipe']:
            cursor.close()
            return {"message": "Seuls les administrateurs ou chefs d'équipe peuvent créer un projet."}, 403

        # Vérifier que tous les membres d'équipe existent
        invalid_members = [member for member in members if not User.find_by_username(member)]
        if invalid_members:
            cursor.close()
            return {"message": f"Les utilisateurs suivants n'existent pas : {', '.join(invalid_members)}"}, 400

        # Créer le projet
        cursor.execute(
            "INSERT INTO projects (name, description, start_date, end_date, state, created_by) VALUES (%s, %s, %s, %s, %s, %s)",
            (name, description, start_date, end_date, state, created_by)
        )
        project_id = cursor.lastrowid

        # Ajouter les membres de l'équipe
        for member in members:
            cursor.execute(
                "INSERT INTO project_members (project_id, username) VALUES (%s, %s)",
                (project_id, member)
            )

        db.commit()
        cursor.close()
        return {"message": "Projet créé avec succès."}, 201
    
    @staticmethod
    def get_assigned_users(project_name):
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        # Rechercher les utilisateurs assignés à un projet
        cursor.execute("""
            SELECT u.username, u.email, u.role
            FROM users u
            JOIN project_members pm ON u.username = pm.username
            JOIN projects p ON pm.project_id = p.id
            WHERE p.name = %s
        """, (project_name,))
        
        users = cursor.fetchall()
        cursor.close()
        return users

class Task:
    def __init__(self, project_id, task_name, description, priority, status, due_date, created_by):
        self.project_id = project_id
        self.task_name = task_name
        self.description = description
        self.priority = priority
        self.status = status
        self.due_date = due_date
        self.created_by = created_by

    @staticmethod
    def create_task(project_id, task_name, description, priority, status, due_date, created_by):
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO tasks (project_id, task_name, description, priority, status, due_date, created_by) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (project_id, task_name, description, priority, status, due_date, created_by)
        )
        task_id = cursor.lastrowid
        db.commit()
        cursor.close()
        return task_id

    @staticmethod
    def assign_members(task_id, assigned_to):
        db = get_db()
        cursor = db.cursor()
        for member in assigned_to:
            cursor.execute(
                "INSERT INTO task_assignments (task_id, username) VALUES (%s, %s)",
                (task_id, member)
            )
        db.commit()
        cursor.close()
        
    @staticmethod
    def add_dependency(task_name_priority, task_name_dep):
        db = get_db()
        cursor = db.cursor(dictionary=True)

        # Obtenir les tâches par leur nom
        cursor.execute("SELECT * FROM tasks WHERE task_name = %s", (task_name_priority,))
        task_priority = cursor.fetchone()

        cursor.execute("SELECT * FROM tasks WHERE task_name = %s", (task_name_dep,))
        task_dep = cursor.fetchone()

        if not task_priority or not task_dep:
            cursor.close()
            return {"message": "Une ou plusieurs tâches n'ont pas été trouvées."}, 404

        # Vérifier que la dépendance ne crée pas un interblocage
        if Task.has_circular_dependency(task_priority['id'], task_dep['id']):
            cursor.close()
            return {"message": "La dépendance crée un interblocage."}, 400

        # Ajouter la dépendance
        cursor.execute(
            "INSERT INTO task_dependencies (task_id, dependent_task_id) VALUES (%s, %s)",
            (task_priority['id'], task_dep['id'])
        )
        db.commit()
        cursor.close()

        return {"message": "Dépendance ajoutée avec succès."}, 201

    @staticmethod
    def has_circular_dependency(task_id, dependent_id):
        """
        Vérifie s'il existe une dépendance circulaire entre les tâches.
        """
        db = get_db()
        cursor = db.cursor(dictionary=True)

        # Fonction récursive pour vérifier les dépendances
        def check_dependency(current_task_id, target_task_id):
            if current_task_id == target_task_id:
                return True
            cursor.execute("SELECT dependent_task_id FROM task_dependencies WHERE task_id = %s", (current_task_id,))
            dependencies = cursor.fetchall()
            for dependency in dependencies:
                if check_dependency(dependency['dependent_task_id'], target_task_id):
                    return True
            return False

        result = check_dependency(dependent_id, task_id)
        cursor.close()
        return result

    @staticmethod
    def get_assigned_users(task_name):
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        # Rechercher les utilisateurs assignés à une tâche
        cursor.execute("""
            SELECT u.username, u.email, u.role
            FROM users u
            JOIN task_assignments ta ON u.username = ta.username
            JOIN tasks t ON ta.task_id = t.id
            WHERE t.task_name = %s
        """, (task_name,))
        
        users = cursor.fetchall()
        cursor.close()
        return users

class TaskComment:
    def __init__(self, task_id, username, comment):
        self.task_id = task_id
        self.username = username
        self.comment = comment

    @staticmethod
    def add_comment(task_id, username, comment):
        db = get_db()
        cursor = db.cursor()

        # Ajouter le commentaire à la tâche
        cursor.execute(
            "INSERT INTO task_comments (task_id, username, comment) VALUES (%s, %s, %s)",
            (task_id, username, comment)
        )
        db.commit()
        cursor.close()
        return {"message": "Commentaire ajouté avec succès."}, 201

    @staticmethod
    def get_comments(task_id):
        db = get_db()
        cursor = db.cursor(dictionary=True)

        # Obtenir les commentaires de la tâche
        cursor.execute(
            "SELECT * FROM task_comments WHERE task_id = %s ORDER BY created_at ASC",
            (task_id,)
        )
        comments = cursor.fetchall()
        cursor.close()
        return comments

    @staticmethod
    def get_task_comments_with_details(task_name):
        db = get_db()
        cursor = db.cursor(dictionary=True)

        # Rechercher les commentaires de la tâche avec les informations de l'utilisateur
        cursor.execute("""
            SELECT tc.comment, tc.created_at, u.username, u.email, u.role
            FROM task_comments tc
            JOIN tasks t ON tc.task_id = t.id
            JOIN users u ON tc.username = u.username
            WHERE t.task_name = %s
            ORDER BY tc.created_at ASC
        """, (task_name,))
        comments = cursor.fetchall()
        cursor.close()
        return comments


class TimeTracking:
    def __init__(self, task_id, username, start_time, end_time):
        self.task_id = task_id
        self.username = username
        self.start_time = start_time
        self.end_time = end_time

    @staticmethod
    def add_time_entry(task_id, username, start_time, end_time):
        db = get_db()
        cursor = db.cursor()

        # Ajouter une entrée de temps
        cursor.execute(
            "INSERT INTO time_entries (task_id, username, start_time, end_time) VALUES (%s, %s, %s, %s)",
            (task_id, username, start_time, end_time)
        )
        db.commit()
        cursor.close()
        return {"message": "Temps enregistré avec succès."}, 201

    @staticmethod
    def get_time_entries(task_id=None, project_id=None):
        db = get_db()
        cursor = db.cursor(dictionary=True)

        if task_id:
            # Récupérer les entrées de temps pour une tâche spécifique
            cursor.execute("SELECT * FROM time_entries WHERE task_id = %s ORDER BY created_at ASC", (task_id,))
        elif project_id:
            # Récupérer les entrées de temps pour un projet spécifique
            cursor.execute("""
                SELECT te.* FROM time_entries te
                JOIN tasks t ON te.task_id = t.id
                WHERE t.project_id = %s
            """, (project_id,))
        else:
            cursor.close()
            return []

        time_entries = cursor.fetchall()
        cursor.close()
        return time_entries

class Notification:
    def __init__(self, username, message):
        self.username = username
        self.message = message

    @staticmethod
    def add_notification(username, message):
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO notifications (username, message) VALUES (%s, %s)",
            (username, message)
        )
        db.commit()
        cursor.close()

    @staticmethod
    def get_notifications(username):
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM notifications WHERE username = %s ORDER BY created_at DESC",
            (username,)
        )
        notifications = cursor.fetchall()
        cursor.close()
        return notifications

    @staticmethod
    def mark_as_read(notification_id):
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "UPDATE notifications SET is_read = TRUE WHERE id = %s",
            (notification_id,)
        )
        db.commit()
        cursor.close()
