import unittest
from app import create_app
from app.db import get_db

class TaskCommentTestCase(unittest.TestCase):
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
            cursor.execute("DELETE FROM projects WHERE name = 'test_project_comment'")

            # Crée des utilisateurs
            cursor.execute("""
                INSERT INTO users (username, password, email, role)
                VALUES ('test_admin', 'AdminPass123!', 'admin5@example.com', 'administrateur'),
                       ('test_user', 'UserPass123!', 'user5@example.com', 'utilisateur')
            """)

            # Crée un projet
            cursor.execute("""
                INSERT INTO projects (name, description, start_date, end_date, state, created_by)
                VALUES ('test_project_comment', 'Projet pour tester les commentaires', '2024-12-01', '2025-06-30', 'en cours', 'test_admin')
            """)

            # Assigne test_user au projet
            cursor.execute("""
                INSERT INTO project_members (project_id, username)
                VALUES ((SELECT id FROM projects WHERE name = 'test_project_comment'), 'test_user')
            """)

            # Crée une tâche pour le projet
            cursor.execute("""
                INSERT INTO tasks (project_id, task_name, description, priority, status, due_date, created_by)
                VALUES ((SELECT id FROM projects WHERE name = 'test_project_comment'), 'Tâche Test Commentaire', 'Tester les commentaires', 'haute', 'A faire', '2025-06-01', 'test_admin')
            """)

            # Assigne test_user à la tâche
            cursor.execute("""
                INSERT INTO task_assignments (task_id, username)
                VALUES ((SELECT id FROM tasks WHERE task_name = 'Tâche Test Commentaire'), 'test_user')
            """)

            db.commit()
            cursor.close()

    def tearDown(self):
        # Nettoyage des commentaires, des tâches, du projet et des utilisateurs créés durant les tests
        with self.app.app_context():
            db = get_db()
            cursor = db.cursor()

            # Supprime tous les commentaires
            cursor.execute("""
                DELETE FROM task_comments WHERE task_id IN (
                    SELECT id FROM tasks WHERE project_id IN (
                        SELECT id FROM projects WHERE name = 'test_project_comment'
                    )
                )
            """)
            # Supprime les affectations de tâches
            cursor.execute("""
                DELETE FROM task_assignments WHERE task_id IN (
                    SELECT id FROM tasks WHERE project_id IN (
                        SELECT id FROM projects WHERE name = 'test_project_comment'
                    )
                )
            """)
            # Supprime les tâches du projet
            cursor.execute("""
                DELETE FROM tasks WHERE project_id IN (
                    SELECT id FROM projects WHERE name = 'test_project_comment'
                )
            """)
            # Supprime les membres du projet
            cursor.execute("""
                DELETE FROM project_members WHERE project_id IN (
                    SELECT id FROM projects WHERE name = 'test_project_comment'
                )
            """)
            # Supprime le projet
            cursor.execute("DELETE FROM projects WHERE name = 'test_project_comment'")
            # Supprime les utilisateurs
            cursor.execute("DELETE FROM users WHERE username IN ('test_admin', 'test_user')")

            db.commit()
            cursor.close()

    def test_admin_comment_task(self):
        # Teste l'ajout de commentaire par un administrateur sur une tâche
        response = self.client.post('/task/comment', json={
            "username": "test_admin",
            "task_name": "Tâche Test Commentaire",
            "comment": "Commentaire ajouté par l'administrateur."
        })
        self.assertEqual(response.status_code, 201)
        self.assertIn("Commentaire ajouté avec succès", response.get_json()["message"])

    def test_user_comment_assigned_task(self):
        # Teste l'ajout de commentaire par un utilisateur sur une tâche à laquelle il est assigné
        response = self.client.post('/task/comment', json={
            "username": "test_user",
            "task_name": "Tâche Test Commentaire",
            "comment": "Commentaire ajouté par l'utilisateur assigné."
        })
        self.assertEqual(response.status_code, 201)
        self.assertIn("Commentaire ajouté avec succès", response.get_json()["message"])

    def test_user_comment_unassigned_task(self):
        # Teste un cas erroné où un utilisateur tente de commenter une tâche qui n'existe pas (fonctionne aussi si la tâche existe mais il n'y est pas assigné mais sera une erreur 403 avec dans le message "Vous n'avez pas le droit de commenter cette tâche")
        response = self.client.post('/task/comment', json={
            "username": "test_user",
            "task_name": "Tâche Non Assignée",
            "comment": "Tentative de commentaire sur une tâche non assignée."
        })
        self.assertEqual(response.status_code, 404)
        self.assertIn("Tâche non trouvée.", response.get_json()["message"])

if __name__ == '__main__':
    unittest.main()
