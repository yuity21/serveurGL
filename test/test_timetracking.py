import unittest
from app import create_app
from app.db import get_db
from datetime import datetime, timedelta

class TimeTrackingTestCase(unittest.TestCase):
    def setUp(self):
        # Crée une application Flask de test
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

        # Crée un administrateur, un utilisateur, un projet, et une tâche pour les tests
        with self.app.app_context():
            db = get_db()
            cursor = db.cursor()

            # Supprime les utilisateurs et projets existants s'ils existent déjà
            cursor.execute("DELETE FROM users WHERE username IN ('test_admin', 'test_user')")
            cursor.execute("DELETE FROM projects WHERE name = 'test_project_timetracking'")

            # Crée des utilisateurs
            cursor.execute("""
                INSERT INTO users (username, password, email, role)
                VALUES ('test_admin', 'AdminPass123!', 'admin6@example.com', 'administrateur'),
                       ('test_user', 'UserPass123!', 'user6@example.com', 'utilisateur')
            """)

            # Crée un projet
            cursor.execute("""
                INSERT INTO projects (name, description, start_date, end_date, state, created_by)
                VALUES ('test_project_timetracking', 'Projet pour tester le suivi du temps', '2024-12-01', '2025-06-30', 'en cours', 'test_admin')
            """)

            # Assigne test_user au projet
            cursor.execute("""
                INSERT INTO project_members (project_id, username)
                VALUES ((SELECT id FROM projects WHERE name = 'test_project_timetracking'), 'test_user')
            """)

            # Crée une tâche pour le projet
            cursor.execute("""
                INSERT INTO tasks (project_id, task_name, description, priority, status, due_date, created_by)
                VALUES ((SELECT id FROM projects WHERE name = 'test_project_timetracking'), 'Tâche Test TimeTracking', 'Tester le suivi du temps', 'haute', 'A faire', '2025-06-01', 'test_admin')
            """)

            # Assigne test_user à la tâche
            cursor.execute("""
                INSERT INTO task_assignments (task_id, username)
                VALUES ((SELECT id FROM tasks WHERE task_name = 'Tâche Test TimeTracking'), 'test_user')
            """)

            db.commit()
            cursor.close()

    def tearDown(self):
        # Nettoyage des entrées de temps, des tâches, du projet et des utilisateurs créés durant les tests
        with self.app.app_context():
            db = get_db()
            cursor = db.cursor()

            # Supprime toutes les entrées de temps
            cursor.execute("DELETE FROM time_entries WHERE task_id IN (SELECT id FROM tasks WHERE project_id IN (SELECT id FROM projects WHERE name = 'test_project_timetracking'))")
            # Supprime les affectations de tâches
            cursor.execute("DELETE FROM task_assignments WHERE task_id IN (SELECT id FROM tasks WHERE project_id IN (SELECT id FROM projects WHERE name = 'test_project_timetracking'))")
            # Supprime les tâches du projet
            cursor.execute("DELETE FROM tasks WHERE project_id IN (SELECT id FROM projects WHERE name = 'test_project_timetracking')")
            # Supprime les membres du projet
            cursor.execute("DELETE FROM project_members WHERE project_id IN (SELECT id FROM projects WHERE name = 'test_project_timetracking')")
            # Supprime le projet
            cursor.execute("DELETE FROM projects WHERE name = 'test_project_timetracking'")
            # Supprime les utilisateurs
            cursor.execute("DELETE FROM users WHERE username IN ('test_admin', 'test_user')")

            db.commit()
            cursor.close()

    def test_user_time_tracking_valid(self):
        # Teste l'ajout d'une entrée de temps valide par un utilisateur

        response = self.client.post('/task/time/track', json={
            "username": "test_user",
            "task_name": "Tâche Test TimeTracking",
            "start_time": "2024-12-01T09:00:00",
            "end_time": "2024-12-01T16:00:00"
        })
        self.assertEqual(response.status_code, 201)
        self.assertIn("Temps enregistré avec succès", response.get_json()["message"])

    def test_user_time_tracking_invalid_end_time(self):
        # Teste un cas erroné où l'heure de fin est antérieure à l'heure de début

        response = self.client.post('/task/time/track', json={
            "username": "test_user",
            "task_name": "Tâche Test TimeTracking",
            "start_time": "2024-12-01T14:00:00",
            "end_time": "2024-12-01T11:00:00"
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("L'heure de fin doit être postérieure à l'heure de début", response.get_json()["message"])

if __name__ == '__main__':
    unittest.main()
