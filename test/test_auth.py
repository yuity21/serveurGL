import unittest
from app import create_app
from app.models import User
from app.db import get_db

class AuthTestCase(unittest.TestCase):
    def setUp(self):
        # Crée une application Flask de test
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

    def tearDown(self):
        # Nettoyage des ressources spécifiques après chaque test
        with self.app.app_context():
            db = get_db()
            cursor = db.cursor()
            # Suppression des utilisateurs créés pour les tests
            cursor.execute("DELETE FROM users WHERE username LIKE 'testuser_%'")
            db.commit()
            cursor.close()

    def test_register_valid_user(self):
        # Teste l'enregistrement d'un utilisateur valide
        response = self.client.post('/auth/register', json={
            "username": "testuser_valid",
            "password": "StrongPass123!",
            "email": "testuser_valid@example.com",
            "role": "utilisateur"
        })
        self.assertEqual(response.status_code, 201)
        self.assertIn("Utilisateur enregistré avec succès", response.get_json()["message"])

    def test_register_invalid_password(self):
        # Teste un mot de passe non sécurisé
        response = self.client.post('/auth/register', json={
            "username": "testuser_invalidpass",
            "password": "weak",
            "email": "testuser_invalidpass@example.com",
            "role": "utilisateur"
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("Mot de passe non sécurisé", response.get_json()["message"])

    def test_register_invalid_email(self):
        # Teste un email invalide
        response = self.client.post('/auth/register', json={
            "username": "testuser_invalidemail",
            "password": "ValidPass123!",
            "email": "invalid-email",
            "role": "utilisateur"
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("Email invalide", response.get_json()["message"])

    def test_register_invalid_role(self):
        # Teste un rôle non valide
        response = self.client.post('/auth/register', json={
            "username": "testuser_invalidrole",
            "password": "ValidPass123!",
            "email": "testuser_invalidrole@example.com",
            "role": "invalide_role"
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("Rôle non valide", response.get_json()["message"])

    def test_register_existing_user(self):
        # Teste l'enregistrement d'un utilisateur déjà existant
        self.client.post('/auth/register', json={
            "username": "testuser_existing",
            "password": "StrongPass123!",
            "email": "testuser_existing@example.com",
            "role": "utilisateur"
        })
        response = self.client.post('/auth/register', json={
            "username": "testuser_existing",
            "password": "DifferentPass456!",
            "email": "anotheremail@example.com",
            "role": "utilisateur"
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("Nom d'utilisateur déjà pris", response.get_json()["message"])

    def test_login_valid_user(self):
        # Teste la connexion d'un utilisateur enregistré
        # Enregistrement de l'utilisateur
        self.client.post('/auth/register', json={
            "username": "testuser_login",
            "password": "StrongPass123!",
            "email": "testuser_login@example.com",
            "role": "utilisateur"
        })
        # Connexion
        response = self.client.post('/auth/login', json={
            "username": "testuser_login",
            "password": "StrongPass123!"
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("Connexion réussie", response.get_json()["message"])

    def test_login_invalid_password(self):
        # Teste la connexion avec un mot de passe incorrect
        self.client.post('/auth/register', json={
            "username": "testuser_wrongpass",
            "password": "StrongPass123!",
            "email": "testuser_wrongpass@example.com",
            "role": "utilisateur"
        })
        response = self.client.post('/auth/login', json={
            "username": "testuser_wrongpass",
            "password": "WrongPass"
        })
        self.assertEqual(response.status_code, 401)
        self.assertIn("Nom d'utilisateur ou mot de passe incorrect", response.get_json()["message"])

if __name__ == '__main__':
    unittest.main()
