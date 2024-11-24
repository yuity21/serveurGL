CREATE DATABASE serveur;

USE serveur;

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

-- Active l'event scheduler
SET GLOBAL event_scheduler = ON;

-- Création d'un event qui permet que si un projet atteint sa deadline alors il sera automatiquement terminé
CREATE EVENT IF NOT EXISTS update_project_state
ON SCHEDULE EVERY 1 DAY -- Met à jour tous les jours
DO
  UPDATE projects
  SET state = 'terminé'
  WHERE state = 'en cours' AND end_date <= CURDATE();

-- Table des tâches
drop table if exists tasks;
create table tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    task_name VARCHAR(255) NOT NULL,
    description TEXT,
    priority ENUM('haute', 'moyenne', 'basse') NOT NULL,
    status ENUM('A faire', 'en cours', 'terminée') DEFAULT 'A faire',
    due_date DATE,
    created_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (created_by) REFERENCES users(username)
);

-- Table des membres assignés aux tâches
drop table if exists task_assignments;
create table task_assignments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_id INT NOT NULL,
    username VARCHAR(255) NOT NULL,
    FOREIGN KEY (task_id) REFERENCES tasks(id),
    FOREIGN KEY (username) REFERENCES users(username)
);

-- Table des dépendances entre tâches
DROP TABLE IF EXISTS task_dependencies;
CREATE TABLE task_dependencies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_id INT NOT NULL,
    dependent_task_id INT NOT NULL,
    FOREIGN KEY (task_id) REFERENCES tasks(id),
    FOREIGN KEY (dependent_task_id) REFERENCES tasks(id),
    CONSTRAINT chk_no_circular_dependency CHECK (task_id <> dependent_task_id)
);

CREATE TABLE IF NOT EXISTS task_comments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_id INT NOT NULL,
    username VARCHAR(50) NOT NULL,
    comment TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
);

CREATE TABLE time_entries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_id INT,
    username VARCHAR(50),
    start_time DATETIME,
    end_time DATETIME,
    duration_minutes INT GENERATED ALWAYS AS (TIMESTAMPDIFF(MINUTE, start_time, end_time)) VIRTUAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id),
    FOREIGN KEY (username) REFERENCES users(username)
);

CREATE TABLE notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50),
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_read BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (username) REFERENCES users(username)
);


