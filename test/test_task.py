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
            cursor.execute("DELETE FROM projects WHERE name = 'test_project_task'" )  # Supprime le projet s'il existe
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
            # Supprime les notifications créées pendant les tests
            cursor.execute("DELETE FROM notifications WHERE username IN ('test_task_creator', 'test_regular_user')")
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

    def test_create_task_valid(self):
        # Teste la création d'une tâche valide
        response = self.client.post('/task/create', json={
            "username": "test_task_creator",
            "nom_projet": "test_project_task",
            "task_name": "Tâche Test 1",
            "description": "Première tâche du projet.",
            "assigned_to": ["test_regular_user"],
            "priority": "haute",
            "status": "A faire",
            "date_echeance": "2025-03-01"
        })
        self.assertEqual(response.status_code, 201)
        self.assertIn("Tâche créée avec succès", response.get_json()["message"])

    def test_add_dependency_valid(self):
        # Crée des tâches pour tester les dépendances
        with self.app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO tasks (project_id, task_name, description, priority, status, due_date, created_by)
                VALUES ((SELECT id FROM projects WHERE name = 'test_project_task'), 'Tâche Test 1', 'Description A', 'haute', 'A faire', '2025-03-01', 'test_task_creator')
            """)
            cursor.execute("""
                INSERT INTO tasks (project_id, task_name, description, priority, status, due_date, created_by)
                VALUES ((SELECT id FROM projects WHERE name = 'test_project_task'), 'Tâche Test 2', 'Description B', 'moyenne', 'A faire', '2025-04-01', 'test_task_creator')
            """)
            db.commit()
            cursor.close()

        # Ajoute une dépendance de Tâche Test 2 sur Tâche Test 1
        response = self.client.post('/task/add_dependency', json={
            "username": "test_task_creator",
            "task_name_priority": "Tâche Test 1",
            "task_name_dep": "Tâche Test 2"
        })
        self.assertEqual(response.status_code, 201)
        self.assertIn("Dépendance ajoutée avec succès", response.get_json()["message"])

    def test_update_task_state_with_dependency(self):
        # Crée des tâches et une dépendance
        with self.app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO tasks (project_id, task_name, description, priority, status, due_date, created_by)
                VALUES ((SELECT id FROM projects WHERE name = 'test_project_task'), 'Tâche Test 1', 'Description A', 'haute', 'terminée', '2025-03-01', 'test_task_creator')
            """)
            cursor.execute("""
                INSERT INTO tasks (project_id, task_name, description, priority, status, due_date, created_by)
                VALUES ((SELECT id FROM projects WHERE name = 'test_project_task'), 'Tâche Test 2', 'Description B', 'moyenne', 'A faire', '2025-04-01', 'test_task_creator')
            """)
            cursor.execute("""
                INSERT INTO task_dependencies (task_id, dependent_task_id)
                VALUES ((SELECT id FROM tasks WHERE task_name = 'Tâche Test 1'), (SELECT id FROM tasks WHERE task_name = 'Tâche Test 2'))
            """)
            db.commit()
            cursor.close()

        # Essaye de mettre à jour l'état de Tâche Test 2 en "en cours" alors que Tâche Test 1 est terminée
        response = self.client.post('/task/update_state', json={
            "username": "test_task_creator",
            "task_name": "Tâche Test 2",
            "status": "en cours"
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("a été mis à jour", response.get_json()["message"])

    def test_user_permissions(self):
        # Crée une tâche par l'administrateur
        with self.app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO tasks (project_id, task_name, description, priority, status, due_date, created_by)
                VALUES ((SELECT id FROM projects WHERE name = 'test_project_task'), 'Tâche Test 3', 'Description C', 'basse', 'A faire', '2025-05-01', 'test_task_creator')
            """)
            db.commit()
            cursor.close()

        # Essaye de mettre à jour l'état de Tâche Test 3 en "en cours" par un utilisateur normal
        response = self.client.post('/task/update_state', json={
            "username": "test_regular_user",
            "task_name": "Tâche Test 3",
            "status": "en cours"
        })
        self.assertEqual(response.status_code, 403)
        self.assertIn("Vous n'avez pas les droits nécessaires pour modifier cette tâche", response.get_json()["message"])

if __name__ == '__main__':
    unittest.main()
