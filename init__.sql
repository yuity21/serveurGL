CREATE DATABASE serveur;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    role ENUM('administrateur', 'chef d\'équipe', 'utilisateur') NOT NULL
);

CREATE TABLE projects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    state ENUM('en cours', 'terminé') NOT NULL DEFAULT 'en cours',
    created_by VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(username)
);

CREATE TABLE project_members (
    project_id INT,
    username VARCHAR(50),
    PRIMARY KEY (project_id, username),
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (username) REFERENCES users(username)
);
