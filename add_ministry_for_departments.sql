-- For each department that should be joinable, ensure there is a ministry entry:
INSERT INTO Ministries (MinistryName, Description, DepartmentID)
SELECT DepartmentName, Description, DepartmentID
FROM Departments
WHERE DepartmentID NOT IN (SELECT DepartmentID FROM Ministries);
