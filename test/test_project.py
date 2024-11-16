import unittest
from app import create_app
from app.db import get_db

class ProjectTestCase(unittest.TestCase):
    def setUp(self):
        # Crée une application Flask de test
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

        # Crée un utilisateur test qui pourra créer des projets
        with self.app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute("DELETE FROM users WHERE username = 'project_creator'")  # Supprimer l'utilisateur s'il existe déjà
            cursor.execute("""
                INSERT INTO users (username, password, email, role)
                VALUES ('project_creator', 'TestPass123!', 'creator@example.com', 'administrateur')
            """)
            db.commit()
            cursor.close()

    def tearDown(self):
        # Nettoyage des projets créés durant les tests
        with self.app.app_context():
            db = get_db()
            cursor = db.cursor()
            # Supprimer les membres du projet avant de supprimer le projet
            cursor.execute("DELETE FROM project_members WHERE project_id IN (SELECT id FROM projects WHERE name LIKE 'test_project_%')")
            cursor.execute("DELETE FROM projects WHERE name LIKE 'test_project_%'")
            cursor.execute("DELETE FROM users WHERE username = 'project_creator'")
            db.commit()
            cursor.close()

    def test_create_project_valid(self):
        # Teste la création d'un projet valide
        response = self.client.post('/project/create', json={
            "username": "project_creator",  # Utilisateur valide
            "name": "test_project_valid",
            "description": "Description du projet valide",
            "start_date": "2024-11-01",
            "end_date": "2024-12-01",
            "members": ["project_creator"],
            "state": "en cours"
        })
        self.assertEqual(response.status_code, 201)
        self.assertIn("Projet créé avec succès", response.get_json()["message"])

    def test_create_project_invalid_user(self):
        # Teste la création d'un projet par un utilisateur non autorisé
        response = self.client.post('/project/create', json={
            "username": "invalid_user",  # Utilisateur non existant
            "name": "test_project_invaliduser",
            "description": "Description du projet",
            "start_date": "2024-11-01",
            "end_date": "2024-12-01",
            "members": ["project_creator"],
            "state": "en cours"
        })
        self.assertEqual(response.status_code, 403)  # Permission refusée
        self.assertIn("Seuls les administrateurs ou chefs d'équipe peuvent créer un projet.", response.get_json()["message"])

    def test_create_project_missing_fields(self):
        # Teste la création d'un projet avec des champs manquants
        response = self.client.post('/project/create', json={
            "username": "project_creator",
            "name": "",  # Nom manquant
            "description": "Projet avec champs manquants",
            "start_date": "2024-11-01",
            "end_date": "2024-12-01",
            "members": ["project_creator"],
            "state": "en cours"
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("Tous les champs requis doivent être fournis.", response.get_json()["message"])  # Ajusté pour correspondre au message d'erreur

    def test_update_project_status_valid(self):
        # Teste la mise à jour de l'état d'un projet existant
        with self.app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO projects (name, description, start_date, end_date, state, created_by)
                VALUES ('test_project_update', 'Projet à mettre à jour', '2024-11-01', '2024-12-01', 'en cours', 'project_creator')
            """)
            db.commit()
            cursor.close()

        # Mise à jour de l'état du projet
        response = self.client.post('/project/update_state', json={
            "username":"project_creator",
            "project_name": "test_project_update"
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("a été modifié", response.get_json()["message"])

    def test_update_project_status_invalid(self):
        # Teste la mise à jour de l'état d'un projet inexistant
        response = self.client.post('/project/update_state', json={
            "username":"project_creator",
            "project_name": "nonexistent_project"
        })
        self.assertEqual(response.status_code, 404)
        self.assertIn("Projet non trouvé", response.get_json()["message"])

if __name__ == '__main__':
    unittest.main()
