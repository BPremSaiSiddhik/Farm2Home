from flask import Flask, render_template_string, request, redirect, url_for, session, flash
import sqlite3
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Database setup
DB_NAME = 'farm2home.db'

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'customer'
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS crops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            farmer_id INTEGER,
            category TEXT,
            quantity REAL,
            unit TEXT DEFAULT 'kg'
        )
    ''')
    
    # Check if admin exists
    admin = cursor.execute("SELECT * FROM users WHERE role='admin'").fetchone()
    if not admin:
        # Create admin user
        cursor.execute("INSERT INTO users (name, phone, password, role) VALUES (?, ?, ?, ?)",
                       ('Admin User', 'admin', 'admin123', 'admin'))
        
        # Create sample farmers
        cursor.execute("INSERT INTO users (name, phone, password, role) VALUES (?, ?, ?, ?)",
                       ('Venkata Rao', '9000000001', 'pass123', 'farmer'))
        farmer1_id = cursor.lastrowid
        
        cursor.execute("INSERT INTO users (name, phone, password, role) VALUES (?, ?, ?, ?)",
                       ('Lakshmi Devi', '9000000002', 'pass123', 'farmer'))
        farmer2_id = cursor.lastrowid
        
        # Create sample crops
        crops = [
            ('Tomatoes', 35, farmer1_id, 'vegetable', 300, 'kg'),
            ('Brinjal', 28, farmer1_id, 'vegetable', 150, 'kg'),
            ('Onions', 30, farmer1_id, 'vegetable', 500, 'kg'),
            ('Capsicum', 60, farmer2_id, 'vegetable', 100, 'kg'),
            ('Carrots', 40, farmer2_id, 'vegetable', 200, 'kg'),
        ]
        
        for crop in crops:
            cursor.execute("INSERT INTO crops (name, price, farmer_id, category, quantity, unit) VALUES (?, ?, ?, ?, ?, ?)",
                          crop)
        
        conn.commit()
    
    conn.close()

# Decorators
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first!', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Admin access required!', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# HTML Templates
HOME_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Farm2Home</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box;}
        body{font-family:Arial,sans-serif;background:#f5f5f5;}
        nav{background:#2e7d32;padding:15px;color:white;display:flex;justify-content:space-between;align-items:center;}
        nav a{color:white;text-decoration:none;margin:0 10px;}
        .container{padding:20px;max-width:1200px;margin:0 auto;}
        .hero{background:linear-gradient(135deg,#2e7d32,#4caf50);color:white;padding:60px;text-align:center;border-radius:10px;}
        .btn{display:inline-block;padding:10px 20px;background:#ffc107;color:#333;text-decoration:none;border-radius:5px;margin:10px;}
        .products{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:20px;margin-top:30px;}
        .card{background:white;padding:20px;border-radius:10px;box-shadow:0 2px 5px rgba(0,0,0,0.1);}
        .price{color:#2e7d32;font-size:24px;font-weight:bold;}
        .flash{background:#4caf50;color:white;padding:10px;margin:10px 0;border-radius:5px;}
        .error{background:#f44336;}
    </style>
</head>
<body>
    <nav>
        <div><a href="/" style="font-size:24px;font-weight:bold;">🌾 Farm2Home</a></div>
        <div>
            {% if session.user_id %}
                <span>Welcome, {{ session.name }} ({{ session.role }})</span>
                {% if session.role == 'admin' %}
                    <a href="/admin/dashboard">Admin Panel</a>
                {% endif %}
                <a href="/logout">Logout</a>
            {% else %}
                <a href="/login">Login</a>
                <a href="/register">Register</a>
            {% endif %}
        </div>
    </nav>
    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash {{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        <div class="hero">
            <h1>Fresh from Farm to Your Home</h1>
            <p>Direct from farmers - No middlemen!</p>
            <a href="/marketplace" class="btn">Shop Now</a>
            <a href="/register" class="btn">Join as Farmer</a>
        </div>
        
        <h2 style="margin-top:40px;">Featured Products</h2>
        <div class="products">
            {% for crop in crops %}
            <div class="card">
                <h3>{{ crop.name }}</h3>
                <p>By: Farmer {{ crop.farmer_id }}</p>
                <div class="price">₹{{ crop.price }}/{{ crop.unit }}</div>
                <p>Available: {{ crop.quantity }} {{ crop.unit }}</p>
            </div>
            {% endfor %}
        </div>
    </div>
</body>
</html>
'''

LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Login - Farm2Home</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box;}
        body{font-family:Arial,sans-serif;background:#f5f5f5;display:flex;justify-content:center;align-items:center;height:100vh;}
        .login-box{background:white;padding:40px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,0.1);width:350px;}
        input{width:100%;padding:10px;margin:10px 0;border:1px solid #ddd;border-radius:5px;}
        button{width:100%;padding:10px;background:#2e7d32;color:white;border:none;border-radius:5px;cursor:pointer;}
        .info{background:#e3f2fd;padding:15px;margin-top:20px;border-radius:5px;font-size:12px;}
    </style>
</head>
<body>
    <div class="login-box">
        <h2>Login to Farm2Home</h2>
        <form method="POST">
            <input type="text" name="phone" placeholder="Phone Number" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Login</button>
        </form>
        <div class="info">
            <strong>Demo Credentials:</strong><br>
            Admin: admin / admin123<br>
            Farmer: 9000000001 / pass123<br>
            Customer: 9999999999 / pass123
        </div>
        <p style="text-align:center;margin-top:15px;"><a href="/register">Create Account</a></p>
    </div>
</body>
</html>
'''

REGISTER_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Register - Farm2Home</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box;}
        body{font-family:Arial,sans-serif;background:#f5f5f5;display:flex;justify-content:center;align-items:center;height:100vh;}
        .register-box{background:white;padding:40px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,0.1);width:400px;}
        input,select{width:100%;padding:10px;margin:10px 0;border:1px solid #ddd;border-radius:5px;}
        button{width:100%;padding:10px;background:#2e7d32;color:white;border:none;border-radius:5px;cursor:pointer;}
    </style>
</head>
<body>
    <div class="register-box">
        <h2>Create Account</h2>
        <form method="POST">
            <input type="text" name="name" placeholder="Full Name" required>
            <input type="text" name="phone" placeholder="Phone Number" required>
            <input type="password" name="password" placeholder="Password" required>
            <select name="role">
                <option value="customer">Customer</option>
                <option value="farmer">Farmer</option>
            </select>
            <button type="submit">Register</button>
        </form>
        <p style="text-align:center;margin-top:15px;"><a href="/login">Already have an account? Login</a></p>
    </div>
</body>
</html>
'''

MARKETPLACE_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Marketplace - Farm2Home</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box;}
        body{font-family:Arial,sans-serif;background:#f5f5f5;}
        nav{background:#2e7d32;padding:15px;color:white;}
        nav a{color:white;text-decoration:none;margin:0 10px;}
        .container{padding:20px;max-width:1200px;margin:0 auto;}
        .products{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:20px;margin-top:20px;}
        .card{background:white;padding:20px;border-radius:10px;box-shadow:0 2px 5px rgba(0,0,0,0.1);}
        .price{color:#2e7d32;font-size:24px;font-weight:bold;}
        button{background:#2e7d32;color:white;padding:8px 16px;border:none;border-radius:5px;cursor:pointer;}
        .flash{background:#4caf50;color:white;padding:10px;margin:10px 0;border-radius:5px;}
    </style>
</head>
<body>
    <nav>
        <div><a href="/" style="font-size:20px;font-weight:bold;">🌾 Farm2Home</a></div>
        <div>
            {% if session.user_id %}
                <span>Welcome, {{ session.name }}</span>
                <a href="/cart">Cart</a>
                <a href="/logout">Logout</a>
            {% else %}
                <a href="/login">Login</a>
            {% endif %}
        </div>
    </nav>
    <div class="container">
        <h1>Marketplace</h1>
        <div class="products">
            {% for crop in crops %}
            <div class="card">
                <h3>{{ crop.name }}</h3>
                <p>Category: {{ crop.category }}</p>
                <div class="price">₹{{ crop.price }}/{{ crop.unit }}</div>
                <p>Available: {{ crop.quantity }} {{ crop.unit }}</p>
                {% if session.user_id and session.role == 'customer' %}
                <form method="POST" action="/cart/add/{{ crop.id }}">
                    <input type="number" name="quantity" value="1" min="1" style="width:60px;margin:10px 0;">
                    <button type="submit">Add to Cart</button>
                </form>
                {% endif %}
            </div>
            {% endfor %}
        </div>
    </div>
</body>
</html>
'''

ADMIN_DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Admin Dashboard - Farm2Home</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box;}
        body{font-family:Arial,sans-serif;background:#f5f5f5;}
        nav{background:#2e7d32;padding:15px;color:white;}
        nav a{color:white;text-decoration:none;margin:0 10px;}
        .container{padding:20px;max-width:1200px;margin:0 auto;}
        .stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:20px;margin:20px 0;}
        .stat-card{background:white;padding:20px;border-radius:10px;text-align:center;}
        .stat-number{font-size:32px;font-weight:bold;color:#2e7d32;}
        table{width:100%;background:white;border-collapse:collapse;margin-top:20px;}
        th,td{padding:12px;text-align:left;border-bottom:1px solid #ddd;}
        th{background:#2e7d32;color:white;}
        .btn{display:inline-block;padding:5px 10px;background:#ffc107;color:#333;text-decoration:none;border-radius:3px;margin:2px;}
        .btn-danger{background:#f44336;color:white;}
    </style>
</head>
<body>
    <nav>
        <div><a href="/" style="font-size:20px;font-weight:bold;">🌾 Farm2Home Admin</a></div>
        <div>
            <span>Admin: {{ session.name }}</span>
            <a href="/admin/users">Users</a>
            <a href="/admin/crops">Crops</a>
            <a href="/logout">Logout</a>
        </div>
    </nav>
    <div class="container">
        <h1>Admin Dashboard</h1>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{{ stats.total_users }}</div>
                <div>Total Users</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ stats.total_farmers }}</div>
                <div>Farmers</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ stats.total_customers }}</div>
                <div>Customers</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ stats.total_crops }}</div>
                <div>Crops</div>
            </div>
        </div>
        
        <h2>Recent Users</h2>
        <table>
            <thead>
                <tr><th>ID</th><th>Name</th><th>Phone</th><th>Role</th><th>Actions</th></tr>
            </thead>
            <tbody>
                {% for user in users %}
                <tr>
                    <td>{{ user.id }}</td>
                    <td>{{ user.name }}</td>
                    <td>{{ user.phone }}</td>
                    <td>{{ user.role }}</td>
                    <td>
                        <a href="/admin/user/delete/{{ user.id }}" class="btn btn-danger" onclick="return confirm('Delete user?')">Delete</a>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</body>
</html>
'''

CART_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Cart - Farm2Home</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box;}
        body{font-family:Arial,sans-serif;background:#f5f5f5;}
        nav{background:#2e7d32;padding:15px;color:white;}
        nav a{color:white;text-decoration:none;margin:0 10px;}
        .container{padding:20px;max-width:800px;margin:0 auto;}
        .cart-item{background:white;padding:15px;margin:10px 0;border-radius:5px;display:flex;justify-content:space-between;align-items:center;}
        .total{background:white;padding:20px;margin-top:20px;border-radius:5px;font-size:20px;font-weight:bold;}
        button{background:#2e7d32;color:white;padding:10px 20px;border:none;border-radius:5px;cursor:pointer;}
    </style>
</head>
<body>
    <nav>
        <div><a href="/" style="font-size:20px;font-weight:bold;">🌾 Farm2Home</a></div>
        <div><a href="/marketplace">Continue Shopping</a> | <a href="/logout">Logout</a></div>
    </nav>
    <div class="container">
        <h1>Your Cart</h1>
        {% if cart_items %}
            {% for item in cart_items %}
            <div class="cart-item">
                <div>
                    <strong>{{ item.name }}</strong><br>
                    ₹{{ item.price }}/{{ item.unit }} x {{ item.quantity }}
                </div>
                <div>
                    ₹{{ item.total }}
                    <a href="/cart/remove/{{ item.crop_id }}" style="color:red;margin-left:10px;">Remove</a>
                </div>
            </div>
            {% endfor %}
            <div class="total">
                Total: ₹{{ total }}
                <form method="POST" action="/checkout" style="display:inline;float:right;">
                    <button type="submit">Place Order</button>
                </form>
            </div>
        {% else %}
            <p>Your cart is empty. <a href="/marketplace">Shop now</a></p>
        {% endif %}
    </div>
</body>
</html>
'''

# Routes
@app.route('/')
def home():
    conn = get_db()
    crops = conn.execute("SELECT * FROM crops LIMIT 4").fetchall()
    conn.close()
    return render_template_string(HOME_TEMPLATE, crops=crops, session=session)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form['phone']
        password = request.form['password']
        
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE phone=? AND password=?", (phone, password)).fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user['id']
            session['name'] = user['name']
            session['role'] = user['role']
            flash(f'Welcome {user["name"]}!', 'success')
            
            if user['role'] == 'admin':
                return redirect('/admin/dashboard')
            return redirect('/')
        else:
            flash('Invalid credentials!', 'error')
    
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        password = request.form['password']
        role = request.form['role']
        
        conn = get_db()
        try:
            conn.execute("INSERT INTO users (name, phone, password, role) VALUES (?, ?, ?, ?)",
                        (name, phone, password, role))
            conn.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect('/login')
        except sqlite3.IntegrityError:
            flash('Phone number already registered!', 'error')
        finally:
            conn.close()
    
    return render_template_string(REGISTER_TEMPLATE)

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect('/')

@app.route('/marketplace')
def marketplace():
    conn = get_db()
    crops = conn.execute("SELECT * FROM crops").fetchall()
    conn.close()
    return render_template_string(MARKETPLACE_TEMPLATE, crops=crops, session=session)

@app.route('/cart/add/<int:crop_id>', methods=['POST'])
def add_to_cart(crop_id):
    if 'user_id' not in session:
        flash('Please login first!', 'error')
        return redirect('/login')
    
    quantity = int(request.form.get('quantity', 1))
    
    if 'cart' not in session:
        session['cart'] = {}
    
    cart = session['cart']
    if str(crop_id) in cart:
        cart[str(crop_id)] += quantity
    else:
        cart[str(crop_id)] = quantity
    
    session['cart'] = cart
    flash('Added to cart!', 'success')
    return redirect('/marketplace')

@app.route('/cart')
def cart():
    if 'user_id' not in session:
        return redirect('/login')
    
    cart_items = []
    total = 0
    
    if 'cart' in session and session['cart']:
        conn = get_db()
        for crop_id, quantity in session['cart'].items():
            crop = conn.execute("SELECT * FROM crops WHERE id=?", (crop_id,)).fetchone()
            if crop:
                item_total = crop['price'] * quantity
                total += item_total
                cart_items.append({
                    'crop_id': crop_id,
                    'name': crop['name'],
                    'price': crop['price'],
                    'unit': crop['unit'],
                    'quantity': quantity,
                    'total': item_total
                })
        conn.close()
    
    return render_template_string(CART_TEMPLATE, cart_items=cart_items, total=total)

@app.route('/cart/remove/<int:crop_id>')
def remove_from_cart(crop_id):
    if 'cart' in session and str(crop_id) in session['cart']:
        del session['cart'][str(crop_id)]
        flash('Item removed from cart!', 'success')
    return redirect('/cart')

@app.route('/checkout', methods=['POST'])
def checkout():
    if 'user_id' not in session:
        return redirect('/login')
    
    # Clear cart after order
    session['cart'] = {}
    flash('Order placed successfully!', 'success')
    return redirect('/')

# Admin Routes
@app.route('/admin/dashboard')
def admin_dashboard():
    if 'role' not in session or session['role'] != 'admin':
        flash('Admin access required!', 'error')
        return redirect('/login')
    
    conn = get_db()
    stats = {
        'total_users': conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        'total_farmers': conn.execute("SELECT COUNT(*) FROM users WHERE role='farmer'").fetchone()[0],
        'total_customers': conn.execute("SELECT COUNT(*) FROM users WHERE role='customer'").fetchone()[0],
        'total_crops': conn.execute("SELECT COUNT(*) FROM crops").fetchone()[0],
    }
    users = conn.execute("SELECT * FROM users ORDER BY id DESC").fetchall()
    conn.close()
    
    return render_template_string(ADMIN_DASHBOARD_TEMPLATE, stats=stats, users=users, session=session)

@app.route('/admin/users')
def admin_users():
    if 'role' not in session or session['role'] != 'admin':
        return redirect('/login')
    
    conn = get_db()
    users = conn.execute("SELECT * FROM users ORDER BY id DESC").fetchall()
    conn.close()
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head><title>Manage Users</title>
    <style>
        body{font-family:Arial;background:#f5f5f5;}
        table{width:100%;background:white;border-collapse:collapse;}
        th,td{padding:10px;border-bottom:1px solid #ddd;}
        th{background:#2e7d32;color:white;}
        .btn{background:#f44336;color:white;padding:5px 10px;text-decoration:none;border-radius:3px;}
    </style>
    </head>
    <body>
        <h1>Manage Users</h1>
        <table>
            <tr><th>ID</th><th>Name</th><th>Phone</th><th>Role</th><th>Action</th></tr>
            {% for user in users %}
            <tr>
                <td>{{ user.id }}</td>
                <td>{{ user.name }}</td>
                <td>{{ user.phone }}</td>
                <td>{{ user.role }}</td>
                <td><a href="/admin/user/delete/{{ user.id }}" class="btn" onclick="return confirm('Delete?')">Delete</a></td>
            </tr>
            {% endfor %}
        </table>
        <p><a href="/admin/dashboard">Back to Dashboard</a></p>
    </body>
    </html>
    ''', users=users)

@app.route('/admin/crops')
def admin_crops():
    if 'role' not in session or session['role'] != 'admin':
        return redirect('/login')
    
    conn = get_db()
    crops = conn.execute("SELECT * FROM crops").fetchall()
    conn.close()
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head><title>Manage Crops</title>
    <style>
        body{font-family:Arial;background:#f5f5f5;}
        table{width:100%;background:white;border-collapse:collapse;}
        th,td{padding:10px;border-bottom:1px solid #ddd;}
        th{background:#2e7d32;color:white;}
        .btn{background:#f44336;color:white;padding:5px 10px;text-decoration:none;border-radius:3px;}
    </style>
    </head>
    <body>
        <h1>Manage Crops</h1>
        <table>
            <tr><th>ID</th><th>Name</th><th>Price</th><th>Farmer ID</th><th>Action</th></tr>
            {% for crop in crops %}
            <tr>
                <td>{{ crop.id }}</td>
                <td>{{ crop.name }}</td>
                <td>₹{{ crop.price }}</td>
                <td>{{ crop.farmer_id }}</td>
                <td><a href="/admin/crop/delete/{{ crop.id }}" class="btn" onclick="return confirm('Delete?')">Delete</a></td>
            </tr>
            {% endfor %}
        </table>
        <p><a href="/admin/dashboard">Back to Dashboard</a></p>
    </body>
    </html>
    ''', crops=crops)

@app.route('/admin/user/delete/<int:user_id>')
def admin_delete_user(user_id):
    if 'role' not in session or session['role'] != 'admin':
        return redirect('/login')
    
    conn = get_db()
    conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    flash('User deleted!', 'success')
    return redirect('/admin/users')

@app.route('/admin/crop/delete/<int:crop_id>')
def admin_delete_crop(crop_id):
    if 'role' not in session or session['role'] != 'admin':
        return redirect('/login')
    
    conn = get_db()
    conn.execute("DELETE FROM crops WHERE id=?", (crop_id,))
    conn.commit()
    conn.close()
    flash('Crop deleted!', 'success')
    return redirect('/admin/crops')

if __name__ == '__main__':
    init_db()
    print("\n" + "="*50)
    print("✅ Farm2Home Server Started Successfully!")
    print("="*50)
    print("\n🔐 LOGIN CREDENTIALS:")
    print("-"*30)
    print("👑 Admin:    admin / admin123")
    print("👨‍🌾 Farmer:   9000000001 / pass123")
    print("👤 Customer: 9999999999 / pass123")
    print("-"*30)
    print("\n🌐 Open: http://127.0.0.1:5000")
    print("="*50 + "\n")
    app.run(debug=True, port=5000)