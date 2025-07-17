from flask import Flask, Blueprint, render_template, request, redirect, url_for, flash, session, g, jsonify, make_response
import os
import pyodbc
import hashlib
import hmac
from functools import wraps
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import csv
import io

# Initialize Flask app
app = Flask(__name__)

#######################
# CONFIGURATION #
#######################

# Secret key for session
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'your-secret-key-here'

# Database configuration
app.config['DB_SERVER'] = os.environ.get('DB_SERVER') or 'localhost\\SQLEXPRESS'
app.config['DB_NAME'] = os.environ.get('DB_NAME') or 'ecommerce'
app.config['DB_USER'] = os.environ.get('DB_USER') or None  # Using Windows Authentication
app.config['DB_PASSWORD'] = os.environ.get('DB_PASSWORD') or None  # Using Windows Authentication

# File upload configuration
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'csv'}

# Session configuration
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Add built-in functions to Jinja2 environment
app.jinja_env.globals.update(max=max, min=min)

#######################
# SECURITY FUNCTIONS #
#######################

def hash_password(password):
    """Hash a password using PBKDF2 with SHA-256"""
    salt = os.urandom(16)
    iterations = 150000
    
    # Use PBKDF2 with SHA-256
    dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, iterations)
    
    # Format: algorithm:iterations:salt:hash
    password_hash = f"pbkdf2:sha256:{iterations}:{salt.hex()}:{dk.hex()}"
    return password_hash

def verify_password(stored_password, provided_password):
    """Verify a password against its hash"""
    try:
        # Parse the stored password hash
        algorithm, hash_name, iterations, salt, hash_value = stored_password.split(':')
        iterations = int(iterations)
        salt = bytes.fromhex(salt)
        stored_hash = bytes.fromhex(hash_value)
        
        # Hash the provided password
        dk = hashlib.pbkdf2_hmac(hash_name, provided_password.encode(), salt, iterations)
        
        # Compare in constant time to prevent timing attacks
        return hmac.compare_digest(dk, stored_hash)
    except Exception as e:
        print(f"Password verification error: {e}")
        return False

def login_required(f):
    """Decorator to require login for a route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin role for a route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('auth.login'))
        if session.get('role') != 'Admin':
            flash('You do not have permission to access this page', 'danger')
            return redirect(url_for('main.home'))
        return f(*args, **kwargs)
    return decorated_function

#######################
# DATABASE FUNCTIONS #
#######################

def get_db_connection():
    """Create and return a connection to the SQL Server database"""
    conn_str = 'DRIVER={ODBC Driver 17 for SQL Server};'
    conn_str += f'SERVER={app.config["DB_SERVER"]};'
    conn_str += f'DATABASE={app.config["DB_NAME"]};'
    
    # Use SQL Server authentication if provided, otherwise use Windows Authentication
    if app.config['DB_USER'] and app.config['DB_PASSWORD']:
        conn_str += f'UID={app.config["DB_USER"]};'
        conn_str += f'PWD={app.config["DB_PASSWORD"]};'
    else:
        conn_str += 'Trusted_Connection=yes;'
    
    conn = pyodbc.connect(conn_str)
    return conn

def execute_query(query, params=None, fetch=True):
    """Execute a SQL query and return results if needed"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
            
        if fetch:
            results = cursor.fetchall()
            # Convert results to list of dictionaries
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row)) for row in results]
        else:
            conn.commit()
            return cursor.rowcount
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()

def execute_procedure(procedure_name, params=None, fetch=True):
    """Execute a stored procedure and return results if needed"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if params:
            cursor.execute(f"EXEC {procedure_name} {', '.join(['?' for _ in params])}", params)
        else:
            cursor.execute(f"EXEC {procedure_name}")
            
        if fetch:
            results = cursor.fetchall()
            # Convert results to list of dictionaries
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row)) for row in results]
        else:
            conn.commit()
            return cursor.rowcount
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()

#######################
# USER MODEL FUNCTIONS #
#######################

def get_user_by_email(email):
    """Get a user by email"""
    query = "SELECT UserID, FullName, Email, PasswordHash, PhoneNumber, Address, Role, Status FROM Users WHERE Email = ?"
    results = execute_query(query, [email])
    return results[0] if results else None

def create_user(full_name, email, password, phone_number, address):
    """Create a new user"""
    password_hash = hash_password(password)
    
    # First, insert the user
    insert_query = """
    INSERT INTO Users (FullName, Email, PasswordHash, PhoneNumber, Address, Role, Status, CreatedAt)
    VALUES (?, ?, ?, ?, ?, 'Customer', 1, GETDATE())
    """
    
    # Execute the insert without fetching results
    execute_query(insert_query, [full_name, email, password_hash, phone_number, address], fetch=False)
    
    # Then, get the user ID of the newly inserted user
    get_id_query = "SELECT UserID FROM Users WHERE Email = ?"
    results = execute_query(get_id_query, [email])
    
    return results[0]['UserID'] if results else None

def authenticate_user(email, password):
    """Authenticate a user by email and password"""
    user = get_user_by_email(email)
    if user and verify_password(user['PasswordHash'], password):
        return user
    return None

def get_user_by_id(user_id):
    """Get a user by ID"""
    query = "SELECT UserID, FullName, Email, PhoneNumber, Address, Role, Status FROM Users WHERE UserID = ?"
    results = execute_query(query, [user_id])
    return results[0] if results else None

def update_user_profile(user_id, full_name, phone_number, address):
    """Update a user's profile"""
    query = """
    UPDATE Users 
    SET FullName = ?, PhoneNumber = ?, Address = ? 
    WHERE UserID = ?
    """
    return execute_query(query, [full_name, phone_number, address, user_id], fetch=False)

def get_all_users():
    """Get all users (for admin)"""
    query = "SELECT UserID, FullName, Email, PhoneNumber, Role, Status, CreatedAt FROM Users ORDER BY CreatedAt DESC"
    return execute_query(query)

def update_user_role(user_id, role):
    """Update a user's role"""
    query = "UPDATE Users SET Role = ? WHERE UserID = ?"
    return execute_query(query, [role, user_id], fetch=False)

def toggle_user_status(user_id):
    """Toggle a user's status (active/inactive)"""
    query = "UPDATE Users SET Status = ~Status WHERE UserID = ?"
    return execute_query(query, [user_id], fetch=False)

#######################
# PRODUCT MODEL FUNCTIONS #
#######################

def get_featured_products(limit=8):
    """Get featured products for the home page"""
    # SQL Server doesn't allow parameters in TOP directly, so we need to use a different approach
    query = f"SELECT TOP {limit} * FROM Products ORDER BY CreatedAt DESC"
    return execute_query(query)

def get_products(category_id=None, search_term=None, page=1, per_page=12):
    """Get products with optional filtering and pagination"""
    offset = (page - 1) * per_page
    
    # Base query
    query = """
    SELECT p.*, c.CategoryName
    FROM Products p
    JOIN Categories c ON p.CategoryID = c.CategoryID
    WHERE 1=1
    """
    params = []
    
    # Add filters if provided
    if category_id:
        query += " AND p.CategoryID = ?"
        params.append(category_id)
    
    if search_term:
        query += " AND (p.ProductName LIKE ? OR p.Description LIKE ?)"
        search_pattern = f'%{search_term}%'
        params.extend([search_pattern, search_pattern])
    
    # Add ordering and pagination
    query += f" ORDER BY p.CreatedAt DESC OFFSET {offset} ROWS FETCH NEXT {per_page} ROWS ONLY"
    
    return execute_query(query, params)

def get_product_by_id(product_id):
    """Get a product by ID"""
    query = """
    SELECT p.*, c.CategoryName
    FROM Products p
    JOIN Categories c ON p.CategoryID = c.CategoryID
    WHERE p.ProductID = ?
    """
    results = execute_query(query, [product_id])
    return results[0] if results else None

def get_categories():
    """Get all product categories"""
    query = "SELECT * FROM Categories ORDER BY CategoryName"
    return execute_query(query)

def add_product(name, description, price, stock, category_id, image_url):
    """Add a new product"""
    return execute_procedure('sp_AddProduct', [name, description, price, stock, category_id, image_url])

def update_product(product_id, name, description, price, stock, category_id, image_url):
    """Update an existing product"""
    return execute_procedure('sp_UpdateProduct', [product_id, name, description, price, stock, category_id, image_url], fetch=False)

def delete_product(product_id):
    """Delete a product and remove it from all carts first"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Start a transaction
        cursor.execute("BEGIN TRANSACTION")
        
        # First, check if the product is in any carts
        cursor.execute("SELECT COUNT(*) FROM CartItems WHERE ProductID = ?", [product_id])
        cart_count = cursor.fetchone()[0]
        
        # If product is in carts, remove it from all carts first
        if cart_count > 0:
            cursor.execute("DELETE FROM CartItems WHERE ProductID = ?", [product_id])
        
        # Now delete the product
        cursor.execute("DELETE FROM Products WHERE ProductID = ?", [product_id])
        
        # Commit the transaction
        cursor.execute("COMMIT TRANSACTION")
        conn.commit()
        return True
        
    except Exception as e:
        # Rollback on error
        cursor.execute("ROLLBACK TRANSACTION")
        conn.rollback()
        print(f"Error deleting product: {e}")
        return False
        
    finally:
        cursor.close()
        conn.close()

def count_products(category_id=None, search_term=None):
    """Count total products with optional filtering (for pagination)"""
    query = "SELECT COUNT(*) AS total FROM Products WHERE 1=1"
    params = []
    
    if category_id:
        query += " AND CategoryID = ?"
        params.append(category_id)
    
    if search_term:
        query += " AND (ProductName LIKE ? OR Description LIKE ?)"
        search_pattern = f'%{search_term}%'
        params.extend([search_pattern, search_pattern])
    
    result = execute_query(query, params)
    return result[0]['total'] if result else 0

def bulk_upload_products(csv_data, has_header=True, skip_existing=True):
    """Upload multiple products from CSV data with improved handling of long text"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    success_count = 0
    error_count = 0
    skip_count = 0
    error_details = []
    
    try:
        # Skip header row if needed
        if has_header:
            next(csv_data)
        
        for row_index, row in enumerate(csv_data, start=1):
            try:
                # Check if we have all required fields
                if len(row) < 5:
                    error_count += 1
                    error_details.append(f"Row {row_index}: Insufficient columns (minimum 5 required)")
                    continue
                
                # Get and validate data from CSV
                product_name = row[0].strip()
                
                # Check product name length - truncate if necessary
                if len(product_name) > 250:  # Assuming ProductName is NVARCHAR(255)
                    product_name = product_name[:247] + "..."
                    error_details.append(f"Row {row_index}: Product name truncated (exceeded 250 characters)")
                
                # Validate category_id
                try:
                    category_id = int(row[1])
                except ValueError:
                    error_count += 1
                    error_details.append(f"Row {row_index}: Invalid category ID '{row[1]}'")
                    continue
                
                # Validate price
                try:
                    price = float(row[2])
                except ValueError:
                    error_count += 1
                    error_details.append(f"Row {row_index}: Invalid price '{row[2]}'")
                    continue
                
                # Validate stock quantity
                try:
                    stock_quantity = int(row[3])
                except ValueError:
                    error_count += 1
                    error_details.append(f"Row {row_index}: Invalid stock quantity '{row[3]}'")
                    continue
                
                description = row[4].strip()
                
                # Image URL is optional
                image_url = row[5].strip() if len(row) > 5 else '/static/images/product-placeholder.jpg'
                
                # Check image URL length - truncate if necessary
                if len(image_url) > 500:  # Assuming ImageURL is NVARCHAR(500)
                    image_url = image_url[:497] + "..."
                    error_details.append(f"Row {row_index}: Image URL truncated (exceeded 500 characters)")
                
                # Check if product already exists
                if skip_existing:
                    cursor.execute("SELECT ProductID FROM Products WHERE ProductName = ?", (product_name,))
                    if cursor.fetchone():
                        skip_count += 1
                        continue
                
                # Use parameterized query to handle special characters
                try:
                    cursor.execute("""
                        INSERT INTO Products (ProductName, CategoryID, Price, StockQuantity, Description, ImageURL, CreatedAt)
                        VALUES (?, ?, ?, ?, ?, ?, GETDATE())
                    """, (product_name, category_id, price, stock_quantity, description, image_url))
                    
                    success_count += 1
                except pyodbc.DataError as de:
                    # Handle specific data errors
                    error_count += 1
                    error_details.append(f"Row {row_index}: Data error - {str(de)}")
                except pyodbc.ProgrammingError as pe:
                    # Handle SQL syntax errors
                    error_count += 1
                    error_details.append(f"Row {row_index}: SQL error - {str(pe)}")
                
            except Exception as e:
                error_count += 1
                error_details.append(f"Row {row_index}: {str(e)}")
                # Continue processing other rows instead of stopping
        
        # Commit all successful inserts
        conn.commit()
        
        return {
            'success_count': success_count,
            'error_count': error_count,
            'skip_count': skip_count,
            'error_details': error_details
        }
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()

#######################
# CART MODEL FUNCTIONS #
#######################

def get_cart_items(user_id):
    """Get all items in a user's cart with product details"""
    query = """
    SELECT c.CartItemID, c.UserID, c.Quantity, c.AddedAt,
           p.ProductID, p.ProductName, p.Price, p.ImageURL, p.StockQuantity
    FROM CartItems c
    JOIN Products p ON c.ProductID = p.ProductID
    WHERE c.UserID = ?
    """
    return execute_query(query, [user_id])

def add_to_cart(user_id, product_id, quantity=1):
    """Add an item to the cart or update quantity if it exists"""
    # Check if item already exists in cart
    check_query = "SELECT CartItemID, Quantity FROM CartItems WHERE UserID = ? AND ProductID = ?"
    existing_item = execute_query(check_query, [user_id, product_id])
    
    if existing_item:
        # Update quantity
        update_query = "UPDATE CartItems SET Quantity = Quantity + ? WHERE CartItemID = ?"
        return execute_query(update_query, [quantity, existing_item[0]['CartItemID']], fetch=False)
    else:
        # Add new item
        insert_query = "INSERT INTO CartItems (UserID, ProductID, Quantity) VALUES (?, ?, ?)"
        return execute_query(insert_query, [user_id, product_id, quantity], fetch=False)

def update_cart_quantity(cart_item_id, quantity):
    """Update the quantity of an item in the cart"""
    query = "UPDATE CartItems SET Quantity = ? WHERE CartItemID = ?"
    return execute_query(query, [quantity, cart_item_id], fetch=False)

def remove_from_cart(cart_item_id):
    """Remove an item from the cart"""
    query = "DELETE FROM CartItems WHERE CartItemID = ?"
    return execute_query(query, [cart_item_id], fetch=False)

def clear_cart(user_id):
    """Remove all items from a user's cart"""
    query = "DELETE FROM CartItems WHERE UserID = ?"
    return execute_query(query, [user_id], fetch=False)

def get_cart_total(user_id):
    """Calculate the total price of all items in the cart"""
    query = """
    SELECT SUM(c.Quantity * p.Price) AS TotalAmount
    FROM CartItems c
    JOIN Products p ON c.ProductID = p.ProductID
    WHERE c.UserID = ?
    """
    result = execute_query(query, [user_id])
    return result[0]['TotalAmount'] if result and result[0]['TotalAmount'] else 0

#######################
# ORDER MODEL FUNCTIONS #
#######################

def create_order(user_id, shipping_address):
    """Create a new order from the user's cart items"""
    conn = None
    cursor = None
    
    try:
        # Get connection and cursor
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Start transaction
        cursor.execute("BEGIN TRANSACTION")
        
        # Get cart items
        cart_items = get_cart_items(user_id)
        if not cart_items:
            return None
        
        # Calculate total amount
        total_amount = sum(item['Price'] * item['Quantity'] for item in cart_items)
        
        # Create order
        cursor.execute("""
            INSERT INTO Orders (UserID, TotalAmount, ShippingAddress)
            VALUES (?, ?, ?);
            SELECT SCOPE_IDENTITY() AS OrderID;
        """, (user_id, total_amount, shipping_address))
        
        order_id = cursor.fetchone()[0]
        
        # Create order details
        for item in cart_items:
            cursor.execute("""
                INSERT INTO OrderDetails (OrderID, ProductID, Quantity, UnitPrice)
                VALUES (?, ?, ?, ?);
            """, (order_id, item['ProductID'], item['Quantity'], item['Price']))
        
        # Clear the cart
        cursor.execute("DELETE FROM CartItems WHERE UserID = ?", (user_id,))
        
        # Commit transaction
        cursor.execute("COMMIT TRANSACTION")
        
        return order_id
    
    except Exception as e:
        # Rollback on error
        if cursor:
            cursor.execute("ROLLBACK TRANSACTION")
        raise e
    
    finally:
        # Close connections
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def get_order_by_id(order_id, user_id=None):
    """Get an order by ID, optionally filtering by user ID for security"""
    query = """
    SELECT o.*, u.FullName, u.Email
    FROM Orders o
    JOIN Users u ON o.UserID = u.UserID
    WHERE o.OrderID = ?
    """
    params = [order_id]
    
    if user_id:
        query += " AND o.UserID = ?"
        params.append(user_id)
    
    results = execute_query(query, params)
    if not results:
        return None
    
    order = results[0]
    
    # Get order details
    details_query = """
    SELECT od.*, p.ProductName, p.ImageURL
    FROM OrderDetails od
    JOIN Products p ON od.ProductID = p.ProductID
    WHERE od.OrderID = ?
    """
    order['items'] = execute_query(details_query, [order_id])
    
    return order

def get_user_orders(user_id):
    """Get all orders for a user"""
    query = """
    SELECT OrderID, OrderDate, TotalAmount, Status
    FROM Orders
    WHERE UserID = ?
    ORDER BY OrderDate DESC
    """
    return execute_query(query, [user_id])

def get_all_orders(status=None):
    """Get all orders (for admin), optionally filtered by status"""
    query = """
    SELECT o.OrderID, o.OrderDate, o.TotalAmount, o.Status,
           u.UserID, u.FullName, u.Email
    FROM Orders o
    JOIN Users u ON o.UserID = u.UserID
    """
    params = []
    
    if status:
        query += " WHERE o.Status = ?"
        params.append(status)
    
    query += " ORDER BY o.OrderDate DESC"
    
    return execute_query(query, params)

def update_order_status(order_id, status):
    """Update an order's status"""
    return execute_procedure('sp_UpdateOrderStatus', [order_id, status], fetch=False)

#######################
# HELPER FUNCTIONS #
#######################

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

#######################
# BLUEPRINTS #
#######################

# Create blueprints
main_bp = Blueprint('main', __name__)
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
user_bp = Blueprint('user', __name__, url_prefix='/user')
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
api_bp = Blueprint('api', __name__, url_prefix='/api')

#######################
# BEFORE REQUEST #
#######################

@app.before_request
def load_logged_in_user():
    """Load user data before each request"""
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        g.user = get_user_by_id(user_id)

#######################
# ERROR HANDLERS #
#######################

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors"""
    return render_template('error.html', error_code=404, message="Page not found"), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors"""
    return render_template('error.html', error_code=500, message="Internal server error"), 500

#######################
# MAIN ROUTES #
#######################

@main_bp.route('/')
def home():
    """Home page with featured products"""
    featured_products = get_featured_products(limit=8)
    categories = get_categories()
    return render_template('home.html', products=featured_products, categories=categories)

@main_bp.route('/shop')
def shop():
    """Shop page with product listing and filtering"""
    page = request.args.get('page', 1, type=int)
    category_id = request.args.get('category', None, type=int)
    search = request.args.get('search', None)
    
    # Get products with pagination
    products = get_products(category_id, search, page, per_page=12)
    
    # Get categories for filter
    categories = get_categories()
    
    # Get total products for pagination
    total_products = count_products(category_id, search)
    total_pages = (total_products + 11) // 12  # Ceiling division
    
    return render_template(
        'products.html',
        products=products,
        categories=categories,
        current_category=category_id,
        search_term=search,
        page=page,
        total_pages=total_pages
    )

@main_bp.route('/product/<int:product_id>')
def product_detail(product_id):
    """Product detail page"""
    product = get_product_by_id(product_id)
    if not product:
        flash('Product not found', 'danger')
        return redirect(url_for('main.shop'))
    
    # Get related products (same category)
    related_products = get_products(category_id=product['CategoryID'], per_page=4)
    
    return render_template('product_detail.html', product=product, related_products=related_products)

@main_bp.route('/cart')
def cart():
    """Shopping cart page"""
    if 'user_id' in session:
        cart_items = get_cart_items(session['user_id'])
        total = get_cart_total(session['user_id'])
    else:
        # For non-logged in users, use session cart
        cart_items = session.get('cart', [])
        total = sum(item.get('Price', 0) * item.get('Quantity', 0) for item in cart_items)
    
    return render_template('cart.html', cart_items=cart_items, total=total)

@main_bp.route('/cart/add/<int:product_id>', methods=['POST'])
def cart_add(product_id):
    """Add a product to the cart"""
    quantity = int(request.form.get('quantity', 1))
    
    # Get product to add
    product = get_product_by_id(product_id)
    if not product:
        flash('Product not found', 'danger')
        return redirect(url_for('main.shop'))
    
    # Check stock
    if quantity > product['StockQuantity']:
        flash(f'Sorry, only {product["StockQuantity"]} items available', 'warning')
        return redirect(url_for('main.product_detail', product_id=product_id))
    
    if 'user_id' in session:
        # Add to database cart
        add_to_cart(session['user_id'], product_id, quantity)
    else:
        # Add to session cart for non-logged in users
        cart = session.get('cart', [])
        
        # Check if product already in cart
        for item in cart:
            if item.get('ProductID') == product_id:
                item['Quantity'] += quantity
                session['cart'] = cart
                flash('Cart updated', 'success')
                return redirect(url_for('main.cart'))
        
        # Add new item
        cart.append({
            'ProductID': product_id,
            'ProductName': product['ProductName'],
            'Price': float(product['Price']),
            'ImageURL': product['ImageURL'],
            'Quantity': quantity,
            'StockQuantity': product['StockQuantity']
        })
        session['cart'] = cart
    
    flash('Product added to cart', 'success')
    return redirect(url_for('main.cart'))

@main_bp.route('/cart/update/<int:item_id>', methods=['POST'])
def cart_update(item_id):
    """Update cart item quantity"""
    quantity = int(request.form.get('quantity', 1))
    
    if 'user_id' in session:
        # Update database cart
        update_cart_quantity(item_id, quantity)
    else:
        # Update session cart
        cart = session.get('cart', [])
        for i, item in enumerate(cart):
            if i == item_id:  # Use index as ID for session cart
                item['Quantity'] = quantity
                break
        session['cart'] = cart
    
    flash('Cart updated', 'success')
    return redirect(url_for('main.cart'))

@main_bp.route('/cart/remove/<int:item_id>')
def cart_remove(item_id):
    """Remove item from cart"""
    if 'user_id' in session:
        # Remove from database cart
        remove_from_cart(item_id)
    else:
        # Remove from session cart
        cart = session.get('cart', [])
        if 0 <= item_id < len(cart):
            del cart[item_id]
            session['cart'] = cart
    
    flash('Item removed from cart', 'success')
    return redirect(url_for('main.cart'))

@main_bp.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    """Checkout page and order processing"""
    # Get cart items
    cart_items = get_cart_items(session['user_id'])
    if not cart_items:
        flash('Your cart is empty', 'warning')
        return redirect(url_for('main.shop'))
    
    total = get_cart_total(session['user_id'])
    
    if request.method == 'POST':
        # Process the order
        shipping_address = request.form.get('shipping_address')
        
        # Create order
        order_id = create_order(session['user_id'], shipping_address)
        
        if order_id:
            flash('Order placed successfully!', 'success')
            return redirect(url_for('main.order_confirmation', order_id=order_id))
        else:
            flash('Error creating order', 'danger')
    
    return render_template('checkout.html', cart_items=cart_items, total=total)

@main_bp.route('/order/confirmation/<int:order_id>')
@login_required
def order_confirmation(order_id):
    """Order confirmation page"""
    order = get_order_by_id(order_id, session['user_id'])
    if not order:
        flash('Order not found', 'danger')
        return redirect(url_for('user.orders'))
    
    return render_template('order_confirmation.html', order=order)

#######################
# AUTH ROUTES #
#######################

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page"""
    if request.method == 'POST':
        # Get form data
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        phone_number = request.form.get('phone_number')
        address = request.form.get('address')
        
        # Validate input
        error = None
        if not full_name:
            error = 'Full name is required'
        elif not email:
            error = 'Email is required'
        elif not password:
            error = 'Password is required'
        elif password != confirm_password:
            error = 'Passwords do not match'
        
        # Check if email already exists
        if not error and get_user_by_email(email):
            error = 'Email already registered'
        
        if error:
            flash(error, 'danger')
        else:
            # Create user
            user_id = create_user(full_name, email, password, phone_number, address)
            
            if user_id:
                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for('auth.login'))
            else:
                flash('Error creating user', 'danger')
    
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login page"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        is_admin = request.form.get('is_admin') == 'on'
        
        # Authenticate user
        user = authenticate_user(email, password)
        
        if user:
            # Check if admin login requested but user is not admin
            if is_admin and user['Role'] != 'Admin':
                flash('Invalid admin credentials', 'danger')
                return render_template('login.html')
            
            # Check if account is active
            if not user['Status']:
                flash('Your account has been disabled', 'danger')
                return render_template('login.html')
            
            # Set session
            session.clear()
            session['user_id'] = user['UserID']
            session['role'] = user['Role']
            session.permanent = True
            
            # Redirect based on role
            if user['Role'] == 'Admin':
                return redirect(url_for('admin.dashboard'))
            else:
                # If there was a cart in session, merge it with user's cart
                if 'cart' in session:
                    for item in session.get('cart', []):
                        add_to_cart(user['UserID'], item['ProductID'], item['Quantity'])
                    session.pop('cart', None)
                
                return redirect(url_for('user.dashboard'))
        else:
            flash('Invalid email or password', 'danger')
    
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    """Log out user"""
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('main.home'))

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Forgot password page (simplified for demo)"""
    if request.method == 'POST':
        email = request.form.get('email')
        
        # Check if email exists
        user = get_user_by_email(email)
        if user:
            # In a real app, send password reset email
            flash('Password reset instructions have been sent to your email', 'info')
            return redirect(url_for('auth.login'))
        else:
            flash('Email not found', 'danger')
    
    return render_template('forgot_password.html')

#######################
# USER ROUTES #
#######################

@user_bp.route('/dashboard')
@login_required
def dashboard():
    """User dashboard page"""
    user = get_user_by_id(session['user_id'])
    
    # Get recent orders
    recent_orders = get_user_orders(session['user_id'])[:5]
    
    return render_template('dashboard.html', user=user, recent_orders=recent_orders)

@user_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile page"""
    user = get_user_by_id(session['user_id'])
    
    if request.method == 'POST':
        # Update profile
        full_name = request.form.get('full_name')
        phone_number = request.form.get('phone_number')
        address = request.form.get('address')
        
        if update_user_profile(session['user_id'], full_name, phone_number, address):
            flash('Profile updated successfully', 'success')
            return redirect(url_for('user.profile'))
        else:
            flash('Error updating profile', 'danger')
    
    return render_template('profile.html', user=user)

@user_bp.route('/orders')
@login_required
def orders():
    """User orders page"""
    orders_list = get_user_orders(session['user_id'])
    return render_template('orders.html', orders=orders_list)

@user_bp.route('/order/<int:order_id>')
@login_required
def order_detail(order_id):
    """Order detail page"""
    order = get_order_by_id(order_id, session['user_id'])
    
    if not order:
        flash('Order not found', 'danger')
        return redirect(url_for('user.orders'))
    
    return render_template('order_detail.html', order=order)

#######################
# ADMIN ROUTES #
#######################

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """Admin dashboard page"""
    # Get dashboard metrics
    metrics = execute_query("SELECT * FROM vw_AdminDashboardMetrics")[0]
    
    # Ensure metrics values are not None
    metrics['TotalCustomers'] = metrics['TotalCustomers'] or 0
    metrics['TotalProducts'] = metrics['TotalProducts'] or 0
    metrics['TotalOrders'] = metrics['TotalOrders'] or 0
    metrics['TotalSales'] = metrics['TotalSales'] or 0
    
    # Get recent orders
    recent_orders = get_all_orders()[:5]
    
    # Get sales by date for chart - using TOP instead of LIMIT for SQL Server
    sales_data = execute_query("SELECT TOP 7 * FROM vw_SalesByDate ORDER BY OrderDay DESC")
    
    # Get top selling products - using TOP instead of LIMIT for SQL Server
    top_products = execute_query("SELECT TOP 5 * FROM vw_TopSellingProducts")
    
    return render_template(
        'admindashboard.html',
        metrics=metrics,
        recent_orders=recent_orders,
        sales_data=sales_data,
        top_products=top_products
    )

@admin_bp.route('/products')
@admin_required
def products():
    """Product management page"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', None)
    
    products_list = get_products(search_term=search, page=page, per_page=20)
    categories = get_categories()
    
    # Calculate total pages for pagination
    total_products = count_products(search_term=search)
    total_pages = (total_products + 19) // 20  # Ceiling division
    
    return render_template(
        'adminproducts.html',
        products=products_list,
        categories=categories,
        search_term=search,
        page=page,
        total_pages=total_pages,
        total_products=total_products
    )

@admin_bp.route('/products/add', methods=['GET', 'POST'])
@admin_required
def add_product_route():
    """Add product page"""
    categories = get_categories()
    
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        description = request.form.get('description')
        price = request.form.get('price')
        stock = request.form.get('stock')
        category_id = request.form.get('category_id')
        
        # Handle image upload
        image_url = '/static/images/placeholder.jpg'  # Default image
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                image_url = '/' + file_path
        
        # Add product
        result = add_product(name, description, price, stock, category_id, image_url)
        
        if result:
            flash('Product added successfully', 'success')
            return redirect(url_for('admin.products'))
        else:
            flash('Error adding product', 'danger')
    
    return render_template('admin/product_form.html', categories=categories, product=None)

@admin_bp.route('/products/bulk-upload', methods=['POST'], endpoint='bulk_upload_products')
@admin_required
def bulk_upload_products_route():
    """Bulk upload products from CSV file with improved error handling"""
    if 'csv_file' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('admin.products'))
    
    file = request.files['csv_file']
    
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('admin.products'))
    
    if file and file.filename.endswith('.csv'):
        try:
            # Read the CSV file with error handling for encoding issues
            try:
                stream = io.StringIO(file.stream.read().decode("UTF8", errors='replace'), newline=None)
            except UnicodeDecodeError:
                flash('Error: The CSV file contains invalid characters. Please ensure it is properly encoded (UTF-8 recommended).', 'danger')
                return redirect(url_for('admin.products'))
                
            csv_data = csv.reader(stream)
            
            # Check if first row is header
            has_header = request.form.get('header_row') == 'on'
            skip_existing = request.form.get('skip_existing') == 'on'
            
            # Process the CSV data
            result = bulk_upload_products(csv_data, has_header, skip_existing)
            
            flash(f'Bulk upload complete: {result["success_count"]} products added, {result["skip_count"]} skipped, {result["error_count"]} errors', 'success')
            
            # If there are errors, show detailed information
            if result["error_count"] > 0 and "error_details" in result:
                for error in result["error_details"][:10]:  # Show first 10 errors
                    flash(error, 'warning')
                if len(result["error_details"]) > 10:
                    flash(f'... and {len(result["error_details"]) - 10} more errors', 'warning')
                    
            return redirect(url_for('admin.products'))
        except Exception as e:
            flash(f'Error processing CSV file: {str(e)}', 'danger')
            return redirect(url_for('admin.products'))
    
    flash('Invalid file format. Please upload a CSV file.', 'danger')
    return redirect(url_for('admin.products'))

@admin_bp.route('/products/csv-template')
@admin_required
def download_csv_template():
    """Download a CSV template for bulk product upload"""
    # Create a CSV template for download
    csv_data = io.StringIO()
    writer = csv.writer(csv_data)
    
    # Write header
    writer.writerow(['product_name', 'category_id', 'price', 'stock_quantity', 'description', 'image_url'])
    
    # Write example row
    writer.writerow(['Example Product (max 250 chars)', '1', '19.99', '100', 'This is an example product description', 'https://example.com/image.jpg (max 500 chars)'])
    
    # Prepare response
    response = make_response(csv_data.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=product_template.csv'
    response.headers['Content-type'] = 'text/csv'
    
    return response

@admin_bp.route('/products/edit/<int:product_id>', methods=['GET', 'POST'])
@admin_required
def edit_product(product_id):
    """Edit product page"""
    product = get_product_by_id(product_id)
    if not product:
        flash('Product not found', 'danger')
        return redirect(url_for('admin.products'))
    
    categories = get_categories()
    
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        description = request.form.get('description')
        price = request.form.get('price')
        stock = request.form.get('stock')
        category_id = request.form.get('category_id')
        
        # Handle image upload
        image_url = product['ImageURL']  # Keep existing image by default
        if 'image' in request.files and request.files['image'].filename:
            file = request.files['image']
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                image_url = '/' + file_path
        
        # Update product
        if update_product(product_id, name, description, price, stock, category_id, image_url):
            flash('Product updated successfully', 'success')
            return redirect(url_for('admin.products'))
        else:
            flash('Error updating product', 'danger')
    
    return render_template('admin/product_form.html', product=product, categories=categories)

@admin_bp.route('/products/delete/<int:product_id>', methods=['POST'])
@admin_required
def delete_product_route(product_id):
    """Delete a product"""
    if delete_product(product_id):
        flash('Product deleted successfully', 'success')
    else:
        flash('Error deleting product', 'danger')
    
    return redirect(url_for('admin.products'))

@admin_bp.route('/orders')
@admin_required
def orders():
    """Order management page"""
    status = request.args.get('status', None)
    
    orders_list = get_all_orders(status)
    
    return render_template('adminorders.html', orders=orders_list, current_status=status)

@admin_bp.route('/orders/<int:order_id>')
@admin_required
def order_detail(order_id):
    """Order detail page"""
    order = get_order_by_id(order_id)
    
    if not order:
        flash('Order not found', 'danger')
        return redirect(url_for('admin.orders'))
    
    return render_template('admin/order_detail.html', order=order)

@admin_bp.route('/orders/update-status/<int:order_id>', methods=['POST'])
@admin_required
def update_order_status_route(order_id):
    """Update order status"""
    status = request.form.get('status')
    
    if update_order_status(order_id, status):
        flash('Order status updated', 'success')
    else:
        flash('Error updating order status', 'danger')
    
    return redirect(url_for('admin.order_detail', order_id=order_id))

@admin_bp.route('/users')
@admin_required
def users():
    """User management page"""
    users_list = get_all_users()
    
    return render_template('admin/users.html', users=users_list)

@admin_bp.route('/users/update-role/<int:user_id>', methods=['POST'])
@admin_required
def update_user_role_route(user_id):
    """Update user role"""
    role = request.form.get('role')
    
    if update_user_role(user_id, role):
        flash('User role updated', 'success')
    else:
        flash('Error updating user role', 'danger')
    
    return redirect(url_for('admin.users'))

@admin_bp.route('/users/toggle-status/<int:user_id>', methods=['POST'])
@admin_required
def toggle_user_status_route(user_id):
    """Toggle user status (active/inactive)"""
    if toggle_user_status(user_id):
        flash('User status updated', 'success')
    else:
        flash('Error updating user status', 'danger')
    
    return redirect(url_for('admin.users'))

@admin_bp.route('/reports')
@admin_required
def reports():
    """Reports and analytics page"""
    # Get date range from request
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)  # Default to last 30 days
    
    if request.args.get('start_date'):
        start_date = datetime.strptime(request.args.get('start_date'), '%Y-%m-%d')
    if request.args.get('end_date'):
        end_date = datetime.strptime(request.args.get('end_date'), '%Y-%m-%d')
    
    # Get sales data
    query = """
    SELECT CAST(OrderDate AS DATE) AS OrderDay, 
           SUM(TotalAmount) AS DailySales, 
           COUNT(*) AS OrderCount
    FROM Orders
    WHERE OrderDate BETWEEN ? AND ?
    GROUP BY CAST(OrderDate AS DATE)
    ORDER BY OrderDay
    """
    sales_data = execute_query(query, [start_date, end_date])
    
    # Get top products - using TOP instead of LIMIT for SQL Server
    query = """
    SELECT TOP 10 p.ProductName, SUM(od.Quantity) AS TotalSold, SUM(od.Quantity * od.UnitPrice) AS Revenue
    FROM OrderDetails od
    JOIN Products p ON od.ProductID = p.ProductID
    JOIN Orders o ON od.OrderID = o.OrderID
    WHERE o.OrderDate BETWEEN ? AND ?
    GROUP BY p.ProductName
    ORDER BY TotalSold DESC
    """
    top_products = execute_query(query, [start_date, end_date])
    
    # Get sales by category
    query = """
    SELECT c.CategoryName, SUM(od.Quantity * od.UnitPrice) AS Revenue
    FROM OrderDetails od
    JOIN Products p ON od.ProductID = p.ProductID
    JOIN Categories c ON p.CategoryID = c.CategoryID
    JOIN Orders o ON od.OrderID = o.OrderID
    WHERE o.OrderDate BETWEEN ? AND ?
    GROUP BY c.CategoryName
    ORDER BY Revenue DESC
    """
    category_sales = execute_query(query, [start_date, end_date])
    
    return render_template(
        'admin/reports.html',
        sales_data=sales_data,
        top_products=top_products,
        category_sales=category_sales,
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d')
    )

@admin_bp.route('/reports/export', methods=['POST'])
@admin_required
def export_report():
    """Export report data as CSV"""
    report_type = request.form.get('report_type')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    
    # In a real app, generate CSV file here
    
    flash('Report exported successfully', 'success')
    return redirect(url_for('admin.reports'))

@admin_bp.route('/categories', methods=['GET', 'POST'])
@admin_required
def categories():
    """Category management page"""
    if request.method == 'POST':
        category_name = request.form.get('category_name')
        description = request.form.get('description')
        
        # Add category
        query = """
        INSERT INTO Categories (CategoryName, Description)
        VALUES (?, ?)
        """
        execute_query(query, [category_name, description], fetch=False)
        flash('Category added successfully', 'success')
        return redirect(url_for('admin.categories'))
    
    # Get all categories
    categories_list = get_categories()
    
    return render_template('admin/categories.html', categories=categories_list)

@admin_bp.route('/categories/edit/<int:category_id>', methods=['GET', 'POST'])
@admin_required
def edit_category(category_id):
    """Edit category page"""
    # Get category
    query = "SELECT * FROM Categories WHERE CategoryID = ?"
    category = execute_query(query, [category_id])
    
    if not category:
        flash('Category not found', 'danger')
        return redirect(url_for('admin.categories'))
    
    category = category[0]
    
    if request.method == 'POST':
        category_name = request.form.get('category_name')
        description = request.form.get('description')
        
        # Update category
        query = """
        UPDATE Categories
        SET CategoryName = ?, Description = ?
        WHERE CategoryID = ?
        """
        execute_query(query, [category_name, description, category_id], fetch=False)
        flash('Category updated successfully', 'success')
        return redirect(url_for('admin.categories'))
    
    return render_template('admin/category_form.html', category=category)

@admin_bp.route('/categories/delete/<int:category_id>', methods=['POST'])
@admin_required
def delete_category(category_id):
    """Delete a category"""
    # Check if category has products
    query = "SELECT COUNT(*) AS count FROM Products WHERE CategoryID = ?"
    result = execute_query(query, [category_id])
    
    if result[0]['count'] > 0:
        flash('Cannot delete category with products', 'danger')
        return redirect(url_for('admin.categories'))
    
    # Delete category
    query = "DELETE FROM Categories WHERE CategoryID = ?"
    execute_query(query, [category_id], fetch=False)
    flash('Category deleted successfully', 'success')
    return redirect(url_for('admin.categories'))

@admin_bp.route('/settings', methods=['GET', 'POST'])
@admin_required
def settings():
    """Admin settings page"""
    if request.method == 'POST':
        # Update settings
        # This is a placeholder for actual settings implementation
        flash('Settings updated successfully', 'success')
        return redirect(url_for('admin.settings'))
    
    return render_template('admin/settings.html')

#######################
# API ROUTES #
#######################

@api_bp.route('/products/search')
def search_products():
    """API endpoint for product search (for AJAX)"""
    search_term = request.args.get('term', '')
    category_id = request.args.get('category', None, type=int)
    
    products = get_products(category_id, search_term, page=1, per_page=10)
    
    return jsonify({
        'products': products
    })

@api_bp.route('/cart/add', methods=['POST'])
def add_to_cart_api():
    """API endpoint to add item to cart (for AJAX)"""
    data = request.get_json()
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)
    
    if not product_id:
        return jsonify({'success': False, 'message': 'Product ID is required'}), 400
    
    # Get product to add
    product = get_product_by_id(product_id)
    if not product:
        return jsonify({'success': False, 'message': 'Product not found'}), 404
    
    # Check stock
    if quantity > product['StockQuantity']:
        return jsonify({
            'success': False, 
            'message': f'Only {product["StockQuantity"]} items available'
        }), 400
    
    if 'user_id' in session:
        # Add to database cart
        add_to_cart(session['user_id'], product_id, quantity)
        
        # Get updated cart count
        cart_items = get_cart_items(session['user_id'])
        cart_count = sum(item['Quantity'] for item in cart_items)
        cart_total = get_cart_total(session['user_id'])
        
        return jsonify({
            'success': True,
            'message': 'Product added to cart',
            'cart_count': cart_count,
            'cart_total': cart_total
        })
    else:
        # Add to session cart
        cart = session.get('cart', [])
        
        # Check if product already in cart
        for item in cart:
            if item.get('ProductID') == product_id:
                item['Quantity'] += quantity
                session['cart'] = cart
                
                cart_count = sum(item['Quantity'] for item in cart)
                cart_total = sum(item['Price'] * item['Quantity'] for item in cart)
                
                return jsonify({
                    'success': True,
                    'message': 'Cart updated',
                    'cart_count': cart_count,
                    'cart_total': cart_total
                })
        
        # Add new item
        cart.append({
            'ProductID': product_id,
            'ProductName': product['ProductName'],
            'Price': float(product['Price']),
            'ImageURL': product['ImageURL'],
            'Quantity': quantity,
            'StockQuantity': product['StockQuantity']
        })
        session['cart'] = cart
        
        cart_count = sum(item['Quantity'] for item in cart)
        cart_total = sum(item['Price'] * item['Quantity'] for item in cart)
        
        return jsonify({
            'success': True,
            'message': 'Product added to cart',
            'cart_count': cart_count,
            'cart_total': cart_total
        })

@api_bp.route('/cart/count')
def get_cart_count():
    """API endpoint to get cart count (for AJAX)"""
    if 'user_id' in session:
        cart_items = get_cart_items(session['user_id'])
        count = sum(item['Quantity'] for item in cart_items)
    else:
        cart = session.get('cart', [])
        count = sum(item.get('Quantity', 0) for item in cart)
    
    return jsonify({'count': count})

# Register blueprints
app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(user_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(api_bp)

# Run the application
if __name__ == '__main__':
    app.run(debug=True)