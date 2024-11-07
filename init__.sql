CREATE DATABASE serveur;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    role ENUM('administrateur', 'chef d\'équipe', 'utilisateur') NOT NULL
);
--optionnel et inutile depuis bcrypt qui hache les mots de passes car connection a ses comptes impossible car non encodé--
INSERT INTO users (username, password, email, role) VALUES
('testuser1', 'password123', 'test1@example.com', 'administrateur'),
('testuser2', 'securepass', 'test2@example.com', 'chef d\'équipe'),
('testuser3', 'mypassword', 'test3@example.com', 'utilisateur');

SELECT * FROM users ;