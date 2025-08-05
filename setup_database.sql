-- Ensure the database exists
IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'THE_CLOSET_FAMILY')
BEGIN
    CREATE DATABASE THE_CLOSET_FAMILY;
END;
GO

USE THE_CLOSET_FAMILY;
GO

-- Create Users table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Users' AND xtype='U')
BEGIN
    CREATE TABLE Users (
        UserID INT PRIMARY KEY IDENTITY(1,1),
        Username NVARCHAR(50) NOT NULL UNIQUE,
        PasswordHash NVARCHAR(255) NOT NULL,
        Email NVARCHAR(100) NOT NULL,
        CreatedDate DATETIME NOT NULL DEFAULT GETDATE(),
        LastLoginDate DATETIME NULL
    );
END;

-- Add Role column to Users table if it doesn't exist
IF NOT EXISTS (
    SELECT 1 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_NAME = 'Users' AND COLUMN_NAME = 'Role'
)
BEGIN
    ALTER TABLE Users ADD Role NVARCHAR(20) NOT NULL DEFAULT 'Member';
END;

-- Insert default admin user
INSERT INTO Users (Username, PasswordHash, Email)
SELECT 'admin', HASHBYTES('SHA2_256', 'admin123'), 'admin@example.com'
WHERE NOT EXISTS (SELECT * FROM Users WHERE Username = 'admin');

-- Update default admin user to have the Admin role
UPDATE Users
SET Role = 'Admin'
WHERE Username = 'admin';

-- Insert a test user into the Users table
INSERT INTO Users (Username, PasswordHash, Email)
SELECT 'Pastor Larry', HASHBYTES('SHA2_256', 'PL123'), 'Larry.closetfamily@yahoo.com'
WHERE NOT EXISTS (SELECT * FROM Users WHERE Username = 'Pastor Larry');

-- Update test user to have the Member role
UPDATE Users
SET Role = 'Member'
WHERE Username = 'Pastor Larry';

-- Create Roles table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Roles' AND xtype='U')
BEGIN
    CREATE TABLE Roles (
        RoleID INT PRIMARY KEY IDENTITY(1,1),
        RoleName NVARCHAR(50) NOT NULL,
        Description NVARCHAR(200) NULL
    );
END;

-- Create Permissions table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Permissions' AND xtype='U')
BEGIN
    CREATE TABLE Permissions (
        PermissionID INT PRIMARY KEY IDENTITY(1,1),
        PermissionName NVARCHAR(50) NOT NULL,
        Description NVARCHAR(200) NULL
    );
END;

-- Create RolePermissions table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='RolePermissions' AND xtype='U')
BEGIN
    CREATE TABLE RolePermissions (
        RoleID INT NOT NULL,
        PermissionID INT NOT NULL,
        PRIMARY KEY (RoleID, PermissionID),
        FOREIGN KEY (RoleID) REFERENCES Roles(RoleID),
        FOREIGN KEY (PermissionID) REFERENCES Permissions(PermissionID)
    );
END;

-- Create UserRoles table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='UserRoles' AND xtype='U')
BEGIN
    CREATE TABLE UserRoles (
        UserID INT NOT NULL,
        RoleID INT NOT NULL,
        PRIMARY KEY (UserID, RoleID),
        FOREIGN KEY (UserID) REFERENCES Users(UserID),
        FOREIGN KEY (RoleID) REFERENCES Roles(RoleID)
    );
END;

-- Create Members table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Members' AND xtype='U')
BEGIN
    CREATE TABLE Members (
        MemberID INT PRIMARY KEY IDENTITY(1,1),
        FirstName NVARCHAR(50) NOT NULL,
        LastName NVARCHAR(50) NOT NULL,
        Email NVARCHAR(100) NOT NULL,
        Phone NVARCHAR(20) NULL,
        Address NVARCHAR(200) NULL,
        Country NVARCHAR(100) NULL,
        JoinDate DATETIME NOT NULL DEFAULT GETDATE()
    );
END;

-- Add Birthday column to Members table if it doesn't exist
IF NOT EXISTS (
    SELECT 1 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_NAME = 'Members' AND COLUMN_NAME = 'Birthday'
)
BEGIN
    EXEC('ALTER TABLE Members ADD Birthday DATE NULL');
END;

-- Create Events table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Events' AND xtype='U')
BEGIN
    CREATE TABLE Events (
        EventID INT PRIMARY KEY IDENTITY(1,1),
        EventName NVARCHAR(100) NOT NULL,
        EventDate DATETIME NOT NULL,
        Description NVARCHAR(200) NULL,
        Location NVARCHAR(100) NULL,
        EventImage NVARCHAR(255) NULL
    );
END;

-- Create Attendances table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Attendances' AND xtype='U')
BEGIN
    CREATE TABLE Attendances (
        AttendanceID INT PRIMARY KEY IDENTITY(1,1),
        EventID INT NOT NULL,
        MemberID INT NOT NULL,
        AttendanceDate DATETIME NOT NULL DEFAULT GETDATE(),
        FOREIGN KEY (EventID) REFERENCES Events(EventID),
        FOREIGN KEY (MemberID) REFERENCES Members(MemberID)
    );
END;

-- Create Donations table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Donations' AND xtype='U')
BEGIN
    CREATE TABLE Donations (
        DonationID INT PRIMARY KEY IDENTITY(1,1),
        MemberID INT NOT NULL,
        DonationDate DATETIME NOT NULL DEFAULT GETDATE(),
        Amount DECIMAL(10,2) NOT NULL,
        FOREIGN KEY (MemberID) REFERENCES Members(MemberID)
    );
END;

-- Create Givings table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Givings' AND xtype='U')
BEGIN
    CREATE TABLE Givings (
        DonationID INT PRIMARY KEY IDENTITY(1,1),
        MemberID INT NOT NULL FOREIGN KEY REFERENCES Members(MemberID),
        DonationDate DATETIME NOT NULL DEFAULT GETDATE(),
        Amount DECIMAL(10,2) NOT NULL
    );
END;

-- Create Departments table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Departments' AND xtype='U')
BEGIN
    CREATE TABLE Departments (
        DepartmentID INT PRIMARY KEY IDENTITY(1,1),
        DepartmentName NVARCHAR(50) NOT NULL,
        DepartmentHeads NVARCHAR(100) NULL,
        Description NVARCHAR(200) NULL
    );
END;

-- Create Ministries table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Ministries' AND xtype='U')
BEGIN
    CREATE TABLE Ministries (
        MinistryID INT PRIMARY KEY IDENTITY(1,1),
        MinistryName NVARCHAR(50) NOT NULL,
        Description NVARCHAR(200) NULL,
        DepartmentID INT NOT NULL,
        FOREIGN KEY (DepartmentID) REFERENCES Departments(DepartmentID) ON DELETE CASCADE
    );
END;

-- Create MemberMinistries table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='MemberMinistries' AND xtype='U')
BEGIN
    CREATE TABLE MemberMinistries (
        MemberID INT NOT NULL,
        MinistryID INT NOT NULL,
        PRIMARY KEY (MemberID, MinistryID),
        FOREIGN KEY (MemberID) REFERENCES Members(MemberID),
        FOREIGN KEY (MinistryID) REFERENCES Ministries(MinistryID)
    );
END;

-- Create EventRegistrations table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='EventRegistrations' AND xtype='U')
BEGIN
    CREATE TABLE EventRegistrations (
        EventRegistrationID INT PRIMARY KEY IDENTITY(1,1),
        EventID INT NOT NULL,
        MemberID INT NOT NULL,
        RegistrationDate DATETIME NOT NULL DEFAULT GETDATE(),
        FOREIGN KEY (EventID) REFERENCES Events(EventID),
        FOREIGN KEY (MemberID) REFERENCES Members(MemberID)
    );
END;

-- Create Finances table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Finances' AND xtype='U')
BEGIN
    CREATE TABLE Finances (
        FinanceID INT PRIMARY KEY IDENTITY(1,1),
        TransactionDate DATETIME NOT NULL DEFAULT GETDATE(),
        TransactionType NVARCHAR(50) NOT NULL,
        Amount DECIMAL(10,2) NOT NULL,
        Description NVARCHAR(200) NULL
    );
END;

-- Insert default data
INSERT INTO Roles (RoleName, Description)
SELECT 'Admin', 'Administrator role'
WHERE NOT EXISTS (SELECT * FROM Roles WHERE RoleName = 'Admin');

INSERT INTO Permissions (PermissionName, Description)
SELECT 'ManageUsers', 'Manage users permission'
WHERE NOT EXISTS (SELECT * FROM Permissions WHERE PermissionName = 'ManageUsers');

INSERT INTO Departments (DepartmentName, DepartmentHeads, Description)
SELECT 'Worship', 'Sir Junior', 'Worship department'
WHERE NOT EXISTS (SELECT * FROM Departments WHERE DepartmentName = 'Worship');

-- Insert default data into Finances table
INSERT INTO Finances (TransactionDate, TransactionType, Amount, Description)
SELECT GETDATE(), 'Income', 1000.00, 'Tithes and offerings'
WHERE NOT EXISTS (SELECT * FROM Finances WHERE Description = 'Tithes and offerings');
