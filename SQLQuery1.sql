create database ecommerce

-- Database Schema for E-commerce Application

-- Create Tables
CREATE TABLE Users (
    UserID INT IDENTITY(1,1) PRIMARY KEY,
    FullName NVARCHAR(100) NOT NULL,
    Email NVARCHAR(100) NOT NULL UNIQUE,
    PasswordHash NVARCHAR(255) NOT NULL,
    PhoneNumber NVARCHAR(20),
    Address NVARCHAR(255),
    Role NVARCHAR(20) DEFAULT 'Customer',
    Status BIT DEFAULT 1,
    CreatedAt DATETIME DEFAULT GETDATE()
);



CREATE TABLE Categories (
    CategoryID INT IDENTITY(1,1) PRIMARY KEY,
    CategoryName NVARCHAR(50) NOT NULL,
    Description NVARCHAR(255)
);

CREATE TABLE Products (
    ProductID INT IDENTITY(1,1) PRIMARY KEY,
    ProductName NVARCHAR(100) NOT NULL,
    Description NVARCHAR(MAX),
    Price DECIMAL(10, 2) NOT NULL,
    StockQuantity INT NOT NULL DEFAULT 0,
    CategoryID INT REFERENCES Categories(CategoryID),
    ImageURL NVARCHAR(255),
    CreatedAt DATETIME DEFAULT GETDATE(),
    UpdatedAt DATETIME DEFAULT GETDATE()
);

CREATE TABLE Orders (
    OrderID INT IDENTITY(1,1) PRIMARY KEY,
    UserID INT REFERENCES Users(UserID),
    OrderDate DATETIME DEFAULT GETDATE(),
    TotalAmount DECIMAL(10, 2) NOT NULL,
    Status NVARCHAR(20) DEFAULT 'Pending',
    ShippingAddress NVARCHAR(255)
);

CREATE TABLE OrderDetails (
    OrderDetailID INT IDENTITY(1,1) PRIMARY KEY,
    OrderID INT REFERENCES Orders(OrderID),
    ProductID INT REFERENCES Products(ProductID),
    Quantity INT NOT NULL,
    UnitPrice DECIMAL(10, 2) NOT NULL
);

CREATE TABLE CartItems (
    CartItemID INT IDENTITY(1,1) PRIMARY KEY,
    UserID INT REFERENCES Users(UserID),
    ProductID INT REFERENCES Products(ProductID),
    Quantity INT NOT NULL DEFAULT 1,
    AddedAt DATETIME DEFAULT GETDATE()
);

CREATE TABLE AdminLogs (
    LogID INT IDENTITY(1,1) PRIMARY KEY,
    UserID INT REFERENCES Users(UserID),
    Action NVARCHAR(100) NOT NULL,
    Details NVARCHAR(MAX),
    LoggedAt DATETIME DEFAULT GETDATE()
);

-- Create Indexes
CREATE INDEX IX_Products_CategoryID ON Products(CategoryID);
CREATE INDEX IX_Products_ProductName ON Products(ProductName);
CREATE INDEX IX_Orders_UserID ON Orders(UserID);
CREATE INDEX IX_OrderDetails_OrderID ON OrderDetails(OrderID);
CREATE INDEX IX_OrderDetails_ProductID ON OrderDetails(ProductID);
CREATE INDEX IX_Users_Email ON Users(Email);

-- Create Views
CREATE VIEW vw_AvailableProducts AS
SELECT p.ProductID, p.ProductName, p.Description, p.Price, p.StockQuantity, 
       c.CategoryName, p.ImageURL
FROM Products p
JOIN Categories c ON p.CategoryID = c.CategoryID
WHERE p.StockQuantity > 0;

CREATE VIEW vw_UserOrderHistory AS
SELECT o.OrderID, o.OrderDate, o.TotalAmount, o.Status,
       od.ProductID, od.Quantity, od.UnitPrice,
       p.ProductName, p.ImageURL
FROM Orders o
JOIN OrderDetails od ON o.OrderID = od.OrderID
JOIN Products p ON od.ProductID = p.ProductID;

CREATE VIEW vw_AdminDashboardMetrics AS
SELECT 
    (SELECT COUNT(*) FROM Users WHERE Role = 'Customer') AS TotalCustomers,
    (SELECT COUNT(*) FROM Products) AS TotalProducts,
    (SELECT COUNT(*) FROM Orders) AS TotalOrders,
    (SELECT SUM(TotalAmount) FROM Orders) AS TotalSales;

CREATE VIEW vw_AllOrders AS
SELECT o.OrderID, o.OrderDate, o.TotalAmount, o.Status,
       u.UserID, u.FullName, u.Email
FROM Orders o
JOIN Users u ON o.UserID = u.UserID;

CREATE VIEW vw_SalesByDate AS
SELECT CAST(OrderDate AS DATE) AS OrderDay, SUM(TotalAmount) AS DailySales, COUNT(*) AS OrderCount
FROM Orders
GROUP BY CAST(OrderDate AS DATE);

CREATE VIEW vw_TopSellingProducts AS
SELECT p.ProductID, p.ProductName, SUM(od.Quantity) AS TotalSold, SUM(od.Quantity * od.UnitPrice) AS Revenue
FROM OrderDetails od
JOIN Products p ON od.ProductID = p.ProductID
GROUP BY p.ProductID, p.ProductName
ORDER BY TotalSold DESC;

-- Create Stored Procedures
CREATE PROCEDURE sp_AddUser
    @FullName NVARCHAR(100),
    @Email NVARCHAR(100),
    @PasswordHash NVARCHAR(255),
    @PhoneNumber NVARCHAR(20),
    @Address NVARCHAR(255)
AS
BEGIN
    INSERT INTO Users (FullName, Email, PasswordHash, PhoneNumber, Address)
    VALUES (@FullName, @Email, @PasswordHash, @PhoneNumber, @Address);
    
    SELECT SCOPE_IDENTITY() AS UserID;
END;

CREATE PROCEDURE sp_AuthenticateUser
    @Email NVARCHAR(100)
AS
BEGIN
    SELECT UserID, FullName, Email, PasswordHash, Role, Status
    FROM Users
    WHERE Email = @Email;
END;

CREATE PROCEDURE sp_AddProduct
    @ProductName NVARCHAR(100),
    @Description NVARCHAR(MAX),
    @Price DECIMAL(10, 2),
    @StockQuantity INT,
    @CategoryID INT,
    @ImageURL NVARCHAR(255)
AS
BEGIN
    INSERT INTO Products (ProductName, Description, Price, StockQuantity, CategoryID, ImageURL)
    VALUES (@ProductName, @Description, @Price, @StockQuantity, @CategoryID, @ImageURL);
    
    SELECT SCOPE_IDENTITY() AS ProductID;
END;

CREATE PROCEDURE sp_UpdateProduct
    @ProductID INT,
    @ProductName NVARCHAR(100),
    @Description NVARCHAR(MAX),
    @Price DECIMAL(10, 2),
    @StockQuantity INT,
    @CategoryID INT,
    @ImageURL NVARCHAR(255)
AS
BEGIN
    UPDATE Products
    SET ProductName = @ProductName,
        Description = @Description,
        Price = @Price,
        StockQuantity = @StockQuantity,
        CategoryID = @CategoryID,
        ImageURL = @ImageURL,
        UpdatedAt = GETDATE()
    WHERE ProductID = @ProductID;
END;

CREATE PROCEDURE sp_DeleteProduct
    @ProductID INT
AS
BEGIN
    DELETE FROM Products WHERE ProductID = @ProductID;
END;

CREATE PROCEDURE sp_UpdateOrderStatus
    @OrderID INT,
    @Status NVARCHAR(20)
AS
BEGIN
    UPDATE Orders
    SET Status = @Status
    WHERE OrderID = @OrderID;
END;

CREATE PROCEDURE sp_UpdateUserRole
    @UserID INT,
    @Role NVARCHAR(20)
AS
BEGIN
    UPDATE Users
    SET Role = @Role
    WHERE UserID = @UserID;
END;

CREATE PROCEDURE sp_ToggleUserStatus
    @UserID INT
AS
BEGIN
    UPDATE Users
    SET Status = ~Status
    WHERE UserID = @UserID;
END;

-- Create Triggers
CREATE TRIGGER trg_UpdateProductStock
ON OrderDetails
AFTER INSERT
AS
BEGIN
    UPDATE p
    SET p.StockQuantity = p.StockQuantity - i.Quantity
    FROM Products p
    INNER JOIN inserted i ON p.ProductID = i.ProductID;
END;

CREATE TRIGGER trg_LogProductChanges
ON Products
AFTER UPDATE
AS
BEGIN
    INSERT INTO AdminLogs (UserID, Action, Details)
    VALUES (NULL, 'Product Updated', 
            'Product ID: ' + CAST((SELECT ProductID FROM inserted) AS NVARCHAR(10)) + 
            ', Name: ' + (SELECT ProductName FROM inserted));
END;

CREATE TRIGGER trg_LogUserRegistration
ON Users
AFTER INSERT
AS
BEGIN
    INSERT INTO AdminLogs (UserID, Action, Details)
    VALUES (NULL, 'User Registered', 
            'User ID: ' + CAST((SELECT UserID FROM inserted) AS NVARCHAR(10)) + 
            ', Email: ' + (SELECT Email FROM inserted));
END;

-- Insert sample data
INSERT INTO Categories (CategoryName, Description)
VALUES 
('Electronics', 'Electronic devices and accessories'),
('Clothing', 'Apparel and fashion items'),
('Books', 'Books and publications'),
('Home & Kitchen', 'Home and kitchen products');

-- Insert admin user (password: admin123)
INSERT INTO Users (FullName, Email, PasswordHash, Role)
VALUES ('Admin User', 'admin@example.com', 'pbkdf2:sha256:150000$abc123$abcdef1234567890abcdef1234567890', 'Admin');





UPDATE Users
SET Role = 'Admin'
WHERE Email = 'mkumailraza051@gmail.com';


-------------------------------------------------
-- Update views for SQL Server syntax

-- Drop existing views if they exist
IF OBJECT_ID('vw_SalesByDate', 'V') IS NOT NULL
    DROP VIEW vw_SalesByDate;
GO

IF OBJECT_ID('vw_TopSellingProducts', 'V') IS NOT NULL
    DROP VIEW vw_TopSellingProducts;
GO

-- Recreate views with SQL Server syntax
CREATE VIEW vw_SalesByDate AS
SELECT CAST(OrderDate AS DATE) AS OrderDay, SUM(TotalAmount) AS DailySales, COUNT(*) AS OrderCount
FROM Orders
GROUP BY CAST(OrderDate AS DATE);
GO

CREATE VIEW vw_TopSellingProducts AS
SELECT 
    p.ProductID, 
    p.ProductName, 
    SUM(od.Quantity) AS TotalSold, 
    SUM(od.Quantity * od.UnitPrice) AS Revenue
FROM OrderDetails od
JOIN Products p ON od.ProductID = p.ProductID
GROUP BY p.ProductID, p.ProductName;
GO



ALTER TABLE Products ALTER COLUMN ProductName NVARCHAR(500);

-- Change Description to unlimited text
ALTER TABLE Products ALTER COLUMN Description NVARCHAR(MAX);

-- Increase ImageURL column size to handle longer URLs
ALTER TABLE Products ALTER COLUMN ImageURL NVARCHAR(MAX)



-- Update the delete product stored procedure to handle cart items
ALTER PROCEDURE sp_DeleteProduct
@ProductID INT
AS
BEGIN
    BEGIN TRANSACTION;
    
    BEGIN TRY
        -- First remove the product from all carts
        DELETE FROM CartItems WHERE ProductID = @ProductID;
        
        -- Then delete the product
        DELETE FROM Products WHERE ProductID = @ProductID;
        
        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;



select * from products