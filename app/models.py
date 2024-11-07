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
