# E-commerce Store

A full-featured e-commerce web application built with Flask and SQL Server, featuring both customer and admin interfaces.

## 🚀 Features

### Customer Features
- **User Authentication**: Registration, login, and logout
- **Product Browsing**: View products with categories, search, and pagination
- **Shopping Cart**: Add, update, and remove items
- **Order Management**: Place orders and track order history
- **User Profile**: Update personal information and shipping addresses
- **Product Search**: Search products by name or category

### Admin Features
- **Dashboard**: Overview of sales, orders, and key metrics
- **Product Management**: Add, edit, delete, and bulk upload products
- **Category Management**: Create and manage product categories
- **Order Management**: View and update order status
- **User Management**: Manage user roles and account status
- **Reports**: Sales analytics and reporting
- **Bulk Operations**: CSV import for products

## 🛠️ Technology Stack

- **Backend**: Flask (Python web framework)
- **Database**: Microsoft SQL Server with pyodbc
- **Frontend**: HTML, CSS, JavaScript
- **Authentication**: Session-based with secure password hashing
- **File Upload**: Werkzeug for secure file handling
- **Security**: PBKDF2 password hashing, CSRF protection

## 📋 Prerequisites

- Python 3.7 or higher
- Microsoft SQL Server (SQL Server Express or full version)
- SQL Server ODBC Driver 17

## 🔧 Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/kumailx051/Ecommerce-Store.git
   cd Ecommerce-Store
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # On Windows
   # or
   source venv/bin/activate  # On Linux/Mac
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up SQL Server database**
   - Create a new database named `ecommerce`
   - Run the SQL script `SQLQuery1.sql` to create tables and stored procedures
   - Update database connection settings in `app.py` if needed

5. **Configure environment variables** (optional)
   ```bash
   set SECRET_KEY=your-secret-key-here
   set DB_SERVER=localhost\SQLEXPRESS
   set DB_NAME=ecommerce
   ```

## 🗄️ Database Schema

The application uses the following main tables:
- `Users` - Customer and admin accounts
- `Categories` - Product categories
- `Products` - Product information
- `CartItems` - Shopping cart items
- `Orders` - Order headers
- `OrderDetails` - Order line items

## 🚀 Running the Application

1. **Start the Flask application**
   ```bash
   python app.py
   ```

2. **Access the application**
   - Open your browser and navigate to `http://localhost:5000`
   - Customer interface: `http://localhost:5000`
   - Admin interface: `http://localhost:5000/admin` (login with admin credentials)

## 👥 Default Accounts

After setting up the database, you can create admin and customer accounts through the registration system. The first registered user can be promoted to admin through the database directly.

## 📁 Project Structure

```
Ecommerce-Store/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── SQLQuery1.sql         # Database schema and stored procedures
├── product_template.csv  # CSV template for bulk product upload
├── static/
│   ├── css/              # Stylesheets
│   ├── js/               # JavaScript files
│   └── uploads/          # User uploaded files
├── templates/
│   ├── admin/            # Admin panel templates
│   ├── *.html            # Customer interface templates
└── __pycache__/          # Python cache files
```

## 🔐 Security Features

- **Password Security**: PBKDF2 with SHA-256 hashing
- **Session Management**: Secure session handling with configurable lifetime
- **Input Validation**: SQL injection prevention with parameterized queries
- **File Upload Security**: Secure filename handling and file type validation
- **Access Control**: Role-based access control for admin features

## 📊 Admin Dashboard

The admin dashboard provides:
- Sales metrics and analytics
- Recent orders overview
- Top-selling products
- Sales by category
- User management tools
- Product management with bulk upload

## 🛒 Shopping Cart

- **Session-based**: Cart persists for non-logged-in users
- **Database-backed**: Persistent cart for logged-in users
- **Automatic Sync**: Session cart merges with user cart on login
- **Stock Validation**: Prevents ordering out-of-stock items

## 📦 Product Management

- **Individual Products**: Add/edit products with image upload
- **Bulk Upload**: CSV import with error handling
- **Categories**: Organize products into categories
- **Stock Management**: Track inventory levels
- **Image Handling**: Secure file upload and storage

## 🔍 Search & Filtering

- **Product Search**: Full-text search across product names and descriptions
- **Category Filtering**: Filter products by category
- **Pagination**: Efficient handling of large product catalogs
- **AJAX Support**: Dynamic search without page reload

## 📈 Reporting

- **Sales Reports**: Daily, weekly, and monthly sales data
- **Product Analytics**: Top-selling products and categories
- **Export Functionality**: CSV export of reports
- **Visual Charts**: Dashboard with sales visualizations

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🐛 Known Issues

- Some advanced features may require additional SQL Server configuration
- Large file uploads may need server timeout adjustments
- Mobile responsiveness could be improved in some areas

## 🔮 Future Enhancements

- Payment gateway integration
- Email notifications for orders
- Advanced inventory management
- Multi-language support
- Mobile app development
- Enhanced security features

## 📞 Support

For support, please create an issue in the GitHub repository or contact the development team.

## 🙏 Acknowledgments

- Flask community for excellent documentation
- SQL Server team for robust database features
- Contributors and testers who helped improve the application

---

**Author**: KUMAIL RAZA HUSSAIN IBNE SHAH  
**Repository**: https://github.com/kumailx051/Ecommerce-Store  
**Last Updated**: July 2025
