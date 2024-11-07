from app.db import get_db

class User:
    def __init__(self, username, password, email, role):
        self.username = username
        self.password = password
        self.email = email
        self.role = role

    @staticmethod
    def find_by_username(username):
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        return user

    @staticmethod
    def create_user(username, password, email, role):
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO users (username, password, email, role) VALUES (%s, %s, %s, %s)",
            (username, password, email, role)
        )
        db.commit()
        cursor.close()
