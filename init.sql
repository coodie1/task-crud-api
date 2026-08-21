-- PostgreSQL Table Initialization and Seeding Script

CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    done BOOLEAN NOT NULL DEFAULT FALSE
);

-- Index for searching / filtering
CREATE INDEX IF NOT EXISTS idx_tasks_done ON tasks(done);
CREATE INDEX IF NOT EXISTS idx_tasks_title ON tasks(title);

-- Seed initial tasks if table is empty
INSERT INTO tasks (title, done)
SELECT 'Buy groceries', FALSE
WHERE NOT EXISTS (SELECT 1 FROM tasks WHERE id = 1);

INSERT INTO tasks (title, done)
SELECT 'Read a book', TRUE
WHERE NOT EXISTS (SELECT 1 FROM tasks WHERE id = 2);

INSERT INTO tasks (title, done)
SELECT 'Complete assignment', FALSE
WHERE NOT EXISTS (SELECT 1 FROM tasks WHERE id = 3);
