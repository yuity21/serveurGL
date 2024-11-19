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
