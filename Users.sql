-- Drop all foreign key constraints referencing Users before dropping the table

-- 1. Drop foreign key constraints referencing Users
DECLARE @sql NVARCHAR(MAX) = N'';
SELECT @sql += 'ALTER TABLE [' + OBJECT_SCHEMA_NAME(parent_object_id) + '].[' + OBJECT_NAME(parent_object_id) + '] DROP CONSTRAINT [' + name + '];'
FROM sys.foreign_keys
WHERE referenced_object_id = OBJECT_ID('Users');
EXEC sp_executesql @sql;

-- 2. Now drop the Users table
DROP TABLE IF EXISTS Users;

-- The error means the table 'Users' does not exist in your database.
-- Make sure the table is created before inserting data.

-- 1. Create the Users table if it does not exist:
CREATE TABLE Users (
    UserID INT IDENTITY(1,1) PRIMARY KEY,
    Username NVARCHAR(100) UNIQUE NOT NULL,
    PasswordHash NVARCHAR(255) NOT NULL, -- Store plain password if not hashing
    Email NVARCHAR(255) NOT NULL,
    Role NVARCHAR(50) NOT NULL
);

-- 2. Now insert your admin users:
INSERT INTO Users (Username, PasswordHash, Email, Role) VALUES
    ('admin', 'admin123', 'admin@example.com', 'Admin'),
    ('Sara Mukendi', 'Sara123', 'sara@email.com', 'Admin'),
    ('Nana Amoako', 'Nana124', 'nana@email.com', 'Admin');

-- Insert a sample member user
INSERT INTO Users (Username, PasswordHash, Email, Role) VALUES
    ('john_doe', 'johnpass', 'john@example.com', 'Member');
-- Insert a default admin user only if it does not already exist

INSERT INTO Users (Username, PasswordHash, Email, Role)
SELECT 'admin', 'admin123', 'admin@example.com', 'Admin'
WHERE NOT EXISTS (SELECT 1 FROM Users WHERE Username = 'admin');
