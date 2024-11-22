import unittest
from app import create_app
from app.db import get_db

class TaskTestCase(unittest.TestCase):
    def setUp(self):
        # Crée une application Flask de test
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

        # Crée un utilisateur et un projet pour les tests
        with self.app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute("DELETE FROM users WHERE username = 'test_task_creator'")  # Supprime l'utilisateur s'il existe
            cursor.execute("""
                INSERT INTO users (username, password, email, role)
                VALUES ('test_task_creator', 'TestPass123!', 'creator@example.com', 'administrateur')
            """)
            cursor.execute("DELETE FROM projects WHERE name = 'test_project_task'")  # Supprime le projet s'il existe
            cursor.execute("""
                INSERT INTO projects (name, description, start_date, end_date, state, created_by)
                VALUES ('test_project_task', 'Projet pour tester les tâches', '2024-12-01', '2025-06-30', 'en cours', 'test_task_creator')
            """)
            cursor.execute("DELETE FROM users WHERE username = 'test_regular_user'")
            cursor.execute("""
                INSERT INTO users (username, password, email, role)
                VALUES ('test_regular_user', 'UserPass123!', 'usertest@example.com', 'utilisateur')
            """)
            # Ajoute le test_regular_user au projet
            cursor.execute("""
                INSERT INTO project_members (project_id, username)
                VALUES ((SELECT id FROM projects WHERE name = 'test_project_task'), 'test_regular_user')
            """)
            db.commit()
            cursor.close()

    def tearDown(self):
        # Nettoyage des tâches et du projet créés durant les tests
        with self.app.app_context():
            db = get_db()
            cursor = db.cursor()

            # Supprime toutes les dépendances des tâches
            cursor.execute("DELETE FROM task_dependencies")
            # Supprime toutes les affectations des tâches
            cursor.execute("DELETE FROM task_assignments")
            # Supprime les membres du projet
            cursor.execute("DELETE FROM project_members WHERE project_id IN (SELECT id FROM projects WHERE name = 'test_project_task')")
            # Supprime les tâches du projet
            cursor.execute("DELETE FROM tasks WHERE project_id IN (SELECT id FROM projects WHERE name = 'test_project_task')")
            # Supprime le projet
            cursor.execute("DELETE FROM projects WHERE name = 'test_project_task'")
            # Supprime les utilisateurs
            cursor.execute("DELETE FROM users WHERE username IN ('test_task_creator', 'test_regular_user')")
            
            db.commit()
            cursor.close()

    def test_create_task_invalid_user(self):
        # Teste la création d'une tâche avec un utilisateur non existant
        response = self.client.post('/task/create', json={
            "username": "user_not_exist",
            "nom_projet": "test_project_task",
            "task_name": "Tâche Test 1",
            "description": "Tâche avec utilisateur non existant.",
            "assigned_to": ["test_regular_user"],
            "priority": "haute",
            "status": "A faire",
            "date_echeance": "2025-03-01"
        })
        self.assertEqual(response.status_code, 404)
        self.assertIn("Utilisateur non trouvé", response.get_json()["message"])

    def test_create_task_invalid_member(self):
        # Teste la création d'une tâche avec un membre assigné non existant
        response = self.client.post('/task/create', json={
            "username": "test_task_creator",
            "nom_projet": "test_project_task",
            "task_name": "Tâche Test 2",
            "description": "Tâche avec membre non existant.",
            "assigned_to": ["user_not_exist"],
            "priority": "haute",
            "status": "A faire",
            "date_echeance": "2025-03-01"
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("Les utilisateurs suivants n'existent pas", response.get_json()["message"])

    def test_create_task_invalid_due_date(self):
        # Teste la création d'une tâche avec une date d'échéance au-delà de la date de fin du projet
        response = self.client.post('/task/create', json={
            "username": "test_task_creator",
            "nom_projet": "test_project_task",
            "task_name": "Tâche Test 3",
            "description": "Tâche avec date d'échéance invalide.",
            "assigned_to": ["test_regular_user"],
            "priority": "haute",
            "status": "A faire",
            "date_echeance": "2025-07-01"  # Date après la fin du projet
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("La date d'échéance ne peut pas dépasser la date de fin du projet", response.get_json()["message"])

    def test_add_dependency_nonexistent_task(self):
        # Teste l'ajout de dépendance avec une tâche non existante
        response = self.client.post('/task/add_dependency', json={
            "username": "test_task_creator",
            "task_name_priority": "Tâche Inexistante",
            "task_name_dep": "Tâche Test 1"
        })
        self.assertEqual(response.status_code, 404)
        self.assertIn("Une ou plusieurs tâches n'ont pas été trouvées", response.get_json()["message"])

    def test_add_circular_dependency(self):
        # Crée deux tâches pour tester la dépendance circulaire
        with self.app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO tasks (project_id, task_name, description, priority, status, due_date, created_by)
                VALUES ((SELECT id FROM projects WHERE name = 'test_project_task'), 'Tâche Test 4', 'Description A', 'haute', 'A faire', '2025-03-01', 'test_task_creator')
            """)
            cursor.execute("""
                INSERT INTO tasks (project_id, task_name, description, priority, status, due_date, created_by)
                VALUES ((SELECT id FROM projects WHERE name = 'test_project_task'), 'Tâche Test 5', 'Description B', 'moyenne', 'A faire', '2025-04-01', 'test_task_creator')
            """)
            db.commit()
            cursor.close()

        # Ajoute une dépendance circulaire entre Tâche Test 4 et Tâche Test 5
        response = self.client.post('/task/add_dependency', json={
            "username": "test_task_creator",
            "task_name_priority": "Tâche Test 4",
            "task_name_dep": "Tâche Test 5"
        })
        self.assertEqual(response.status_code, 201)
        self.assertIn("Dépendance ajoutée avec succès", response.get_json()["message"])

        # Essaye d'ajouter la dépendance inverse (créant un cycle)
        response = self.client.post('/task/add_dependency', json={
            "username": "test_task_creator",
            "task_name_priority": "Tâche Test 5",
            "task_name_dep": "Tâche Test 4"
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("La dépendance crée un interblocage", response.get_json()["message"])

if __name__ == '__main__':
    unittest.main()
