from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import sqlite3
import os
from functools import wraps
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'farm2home_secret_key_2025'
DB_PATH = os.path.join(os.path.dirname(__file__), 'farm2home.db')

# ─────────────────────────────────────────
# DATABASE SETUP
# ─────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'customer',  -- 'farmer' or 'customer'
        location TEXT,
        district TEXT,
        language TEXT DEFAULT 'English',
        bank_account TEXT,
        ifsc TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS crops (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        farmer_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        quantity REAL NOT NULL,
        price REAL NOT NULL,
        unit TEXT DEFAULT 'kg',
        harvest_date TEXT,
        location TEXT,
        description TEXT,
        is_organic INTEGER DEFAULT 0,
        min_order REAL DEFAULT 1,
        status TEXT DEFAULT 'active',  -- active, sold_out
        emoji TEXT DEFAULT '🌾',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (farmer_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        farmer_id INTEGER NOT NULL,
        crop_id INTEGER NOT NULL,
        quantity REAL NOT NULL,
        total_price REAL NOT NULL,
        status TEXT DEFAULT 'pending',  -- pending, processing, delivered, cancelled
        delivery_address TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES users(id),
        FOREIGN KEY (farmer_id) REFERENCES users(id),
        FOREIGN KEY (crop_id) REFERENCES crops(id)
    );

    CREATE TABLE IF NOT EXISTS cart (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        crop_id INTEGER NOT NULL,
        quantity REAL NOT NULL DEFAULT 1,
        FOREIGN KEY (customer_id) REFERENCES users(id),
        FOREIGN KEY (crop_id) REFERENCES crops(id),
        UNIQUE(customer_id, crop_id)
    );
    """)

    # Seed demo data
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        farmers = [
            ('Venkata Rao', '9000000001', 'pass123', 'farmer', 'Ongole', 'Prakasam'),
            ('Lakshmi Devi', '9000000002', 'pass123', 'farmer', 'Nellore', 'Nellore'),
            ('Raju Orchards', '9000000003', 'pass123', 'farmer', 'Rajahmundry', 'East Godavari'),
        ]
        cur.executemany("INSERT INTO users (name,phone,password,role,location,district) VALUES (?,?,?,?,?,?)", farmers)

        cur.execute("SELECT COUNT(*) FROM users WHERE role='customer'")
        cur.execute("INSERT INTO users (name,phone,password,role,location,district) VALUES (?,?,?,?,?,?)",
                    ('Demo Customer', '9999999999', 'pass123', 'customer', 'Hyderabad', 'Ranga Reddy'))

        crops_seed = [
            (1,'Tomatoes','vegetable',300,35,'kg','2025-02-20','Ongole, AP','Fresh red tomatoes, no pesticides',1,5,'active','🍅'),
            (1,'Brinjal','vegetable',150,28,'kg','2025-02-22','Ongole, AP','Purple brinjal, farm fresh',0,5,'active','🍆'),
            (1,'Onion','vegetable',500,30,'kg','2025-02-15','Ongole, AP','Red onions, long shelf life',0,10,'active','🧅'),
            (2,'Capsicum','vegetable',100,60,'kg','2025-02-21','Nellore, AP','Colorful capsicums, organically grown',1,3,'active','🫑'),
            (2,'Carrot','vegetable',200,40,'kg','2025-02-19','Nellore, AP','Fresh orange carrots',1,5,'active','🥕'),
            (3,'Alphonso Mango','fruit',80,120,'kg','2025-02-18','Rajahmundry, AP','Premium Alphonso mangoes',1,2,'active','🥭'),
            (3,'Banana','fruit',60,45,'dozen','2025-02-23','Rajahmundry, AP','Fresh bananas, bundles',0,2,'active','🍌'),
            (1,'Green Chili','vegetable',70,80,'kg','2025-02-20','Ongole, AP','Guntur special hot chili',1,2,'active','🌶️'),
            (2,'Corn','vegetable',200,22,'kg','2025-02-17','Nellore, AP','Sweet corn, seasonal',0,5,'active','🌽'),
            (3,'Rice (Sona Masoori)','grain',1000,55,'kg','2025-01-10','Rajahmundry, AP','Premium Sona Masoori rice',0,20,'active','🌾'),
        ]
        cur.executemany("""INSERT INTO crops (farmer_id,name,category,quantity,price,unit,harvest_date,
            location,description,is_organic,min_order,status,emoji) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""", crops_seed)

        orders_seed = [
            (4,1,1,10,350,'delivered','Hyderabad','2025-02-10'),
            (4,2,4,5,300,'delivered','Hyderabad','2025-02-15'),
            (4,1,3,20,600,'processing','Hyderabad','2025-02-20'),
        ]
        cur.executemany("""INSERT INTO orders (customer_id,farmer_id,crop_id,quantity,total_price,status,delivery_address,created_at)
            VALUES (?,?,?,?,?,?,?,?)""", orders_seed)

    conn.commit()
    conn.close()

# ─────────────────────────────────────────
# AUTH HELPERS
# ─────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to continue.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def farmer_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if session.get('role') != 'farmer':
            flash('This page is for farmers only.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

# ─────────────────────────────────────────
# ROUTES – PUBLIC
# ─────────────────────────────────────────
@app.route('/')
def index():
    conn = get_db()
    featured = conn.execute("""
        SELECT c.*, u.name as farmer_name, u.location as farmer_loc
        FROM crops c JOIN users u ON c.farmer_id = u.id
        WHERE c.status='active' LIMIT 6
    """).fetchall()
    stats = {
        'farmers': conn.execute("SELECT COUNT(*) FROM users WHERE role='farmer'").fetchone()[0],
        'customers': conn.execute("SELECT COUNT(*) FROM users WHERE role='customer'").fetchone()[0],
        'crops': conn.execute("SELECT COUNT(*) FROM crops WHERE status='active'").fetchone()[0],
        'orders': conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0],
    }
    conn.close()
    return render_template('index.html', featured=featured, stats=stats)

@app.route('/marketplace')
def marketplace():
    conn = get_db()
    search = request.args.get('search', '')
    category = request.args.get('category', 'all')
    organic = request.args.get('organic', '')

    query = """SELECT c.*, u.name as farmer_name, u.location as farmer_loc
               FROM crops c JOIN users u ON c.farmer_id = u.id
               WHERE c.status='active'"""
    params = []

    if search:
        query += " AND (c.name LIKE ? OR u.name LIKE ? OR c.location LIKE ?)"
        params += [f'%{search}%', f'%{search}%', f'%{search}%']
    if category != 'all':
        query += " AND c.category=?"
        params.append(category)
    if organic:
        query += " AND c.is_organic=1"

    crops = conn.execute(query, params).fetchall()
    conn.close()
    return render_template('marketplace.html', crops=crops, search=search, category=category, organic=organic)

# ─────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────
@app.route('/login', methods=['GET','POST'])
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
            flash(f'Welcome back, {user["name"]}! 🌾', 'success')
            return redirect(url_for('farmer_dashboard' if user['role']=='farmer' else 'index'))
        flash('Invalid phone or password.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        password = request.form['password']
        role = request.form['role']
        location = request.form.get('location','')
        district = request.form.get('district','')
        conn = get_db()
        try:
            conn.execute("INSERT INTO users (name,phone,password,role,location,district) VALUES (?,?,?,?,?,?)",
                         (name, phone, password, role, location, district))
            conn.commit()
            user = conn.execute("SELECT * FROM users WHERE phone=?", (phone,)).fetchone()
            session['user_id'] = user['id']
            session['name'] = user['name']
            session['role'] = user['role']
            flash(f'Welcome to Farm2Home, {name}! 🌾', 'success')
            conn.close()
            return redirect(url_for('farmer_dashboard' if role=='farmer' else 'index'))
        except sqlite3.IntegrityError:
            flash('Phone number already registered.', 'danger')
        conn.close()
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('index'))

# ─────────────────────────────────────────
# CART
# ─────────────────────────────────────────
@app.route('/cart')
@login_required
def cart():
    conn = get_db()
    items = conn.execute("""
        SELECT ca.*, c.name, c.price, c.emoji, c.unit, u.name as farmer_name,
               (ca.quantity * c.price) as line_total
        FROM cart ca
        JOIN crops c ON ca.crop_id = c.id
        JOIN users u ON c.farmer_id = u.id
        WHERE ca.customer_id=?
    """, (session['user_id'],)).fetchall()
    total = sum(i['line_total'] for i in items)
    conn.close()
    return render_template('cart.html', items=items, total=total)

@app.route('/cart/add/<int:crop_id>', methods=['POST'])
@login_required
def add_to_cart(crop_id):
    qty = float(request.form.get('quantity', 1))
    conn = get_db()
    existing = conn.execute("SELECT * FROM cart WHERE customer_id=? AND crop_id=?",
                            (session['user_id'], crop_id)).fetchone()
    if existing:
        conn.execute("UPDATE cart SET quantity=quantity+? WHERE customer_id=? AND crop_id=?",
                     (qty, session['user_id'], crop_id))
    else:
        conn.execute("INSERT INTO cart (customer_id,crop_id,quantity) VALUES (?,?,?)",
                     (session['user_id'], crop_id, qty))
    conn.commit()
    conn.close()
    flash('Added to cart! 🛒', 'success')
    return redirect(request.referrer or url_for('marketplace'))

@app.route('/cart/update/<int:crop_id>', methods=['POST'])
@login_required
def update_cart(crop_id):
    qty = float(request.form.get('quantity', 1))
    conn = get_db()
    if qty <= 0:
        conn.execute("DELETE FROM cart WHERE customer_id=? AND crop_id=?", (session['user_id'], crop_id))
    else:
        conn.execute("UPDATE cart SET quantity=? WHERE customer_id=? AND crop_id=?",
                     (qty, session['user_id'], crop_id))
    conn.commit()
    conn.close()
    return redirect(url_for('cart'))

@app.route('/cart/remove/<int:crop_id>')
@login_required
def remove_from_cart(crop_id):
    conn = get_db()
    conn.execute("DELETE FROM cart WHERE customer_id=? AND crop_id=?", (session['user_id'], crop_id))
    conn.commit()
    conn.close()
    return redirect(url_for('cart'))

@app.route('/cart/count')
def cart_count():
    if 'user_id' not in session:
        return jsonify({'count': 0})
    conn = get_db()
    count = conn.execute("SELECT SUM(quantity) FROM cart WHERE customer_id=?",
                         (session['user_id'],)).fetchone()[0] or 0
    conn.close()
    return jsonify({'count': int(count)})

@app.route('/checkout', methods=['POST'])
@login_required
def checkout():
    conn = get_db()
    items = conn.execute("""
        SELECT ca.*, c.price, c.farmer_id FROM cart ca
        JOIN crops c ON ca.crop_id = c.id WHERE ca.customer_id=?
    """, (session['user_id'],)).fetchall()
    if not items:
        flash('Your cart is empty!', 'warning')
        return redirect(url_for('cart'))
    address = request.form.get('address', 'Default Address')
    for item in items:
        total = item['quantity'] * item['price']
        conn.execute("""INSERT INTO orders (customer_id,farmer_id,crop_id,quantity,total_price,status,delivery_address)
                        VALUES (?,?,?,?,?,?,?)""",
                     (session['user_id'], item['farmer_id'], item['crop_id'],
                      item['quantity'], total, 'pending', address))
    conn.execute("DELETE FROM cart WHERE customer_id=?", (session['user_id'],))
    conn.commit()
    conn.close()
    flash('Order placed successfully! 🎉 Fresh produce on its way!', 'success')
    return redirect(url_for('my_orders'))

# ─────────────────────────────────────────
# CUSTOMER ORDERS
# ─────────────────────────────────────────
@app.route('/orders')
@login_required
def my_orders():
    conn = get_db()
    orders = conn.execute("""
        SELECT o.*, c.name as crop_name, c.emoji, u.name as farmer_name
        FROM orders o
        JOIN crops c ON o.crop_id = c.id
        JOIN users u ON o.farmer_id = u.id
        WHERE o.customer_id=? ORDER BY o.created_at DESC
    """, (session['user_id'],)).fetchall()
    conn.close()
    return render_template('orders.html', orders=orders)

# ─────────────────────────────────────────
# FARMER PORTAL
# ─────────────────────────────────────────
@app.route('/farmer/dashboard')
@farmer_required
def farmer_dashboard():
    conn = get_db()
    listings = conn.execute("SELECT * FROM crops WHERE farmer_id=? ORDER BY created_at DESC",
                            (session['user_id'],)).fetchall()
    incoming = conn.execute("""
        SELECT o.*, c.name as crop_name, c.emoji, u.name as customer_name
        FROM orders o JOIN crops c ON o.crop_id=c.id JOIN users u ON o.customer_id=u.id
        WHERE o.farmer_id=? ORDER BY o.created_at DESC
    """, (session['user_id'],)).fetchall()
    earnings = conn.execute("""
        SELECT SUM(total_price) as total, COUNT(*) as count
        FROM orders WHERE farmer_id=? AND status='delivered'
    """, (session['user_id'],)).fetchone()
    this_month = conn.execute("""
        SELECT SUM(total_price) FROM orders
        WHERE farmer_id=? AND status='delivered' AND strftime('%Y-%m',created_at)=strftime('%Y-%m','now')
    """, (session['user_id'],)).fetchone()[0] or 0
    conn.close()
    return render_template('farmer_dashboard.html',
                           listings=listings, incoming=incoming,
                           earnings=earnings, this_month=this_month)

@app.route('/farmer/crop/add', methods=['GET','POST'])
@farmer_required
def add_crop():
    if request.method == 'POST':
        emoji_map = {
            'vegetable':'🥦','fruit':'🍎','grain':'🌾','pulse':'🫘','spice':'🌿'
        }
        cat = request.form['category']
        conn = get_db()
        conn.execute("""INSERT INTO crops (farmer_id,name,category,quantity,price,unit,harvest_date,
                        location,description,is_organic,min_order,emoji)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                     (session['user_id'],
                      request.form['name'], cat,
                      float(request.form['quantity']),
                      float(request.form['price']),
                      request.form.get('unit','kg'),
                      request.form.get('harvest_date',''),
                      request.form.get('location',''),
                      request.form.get('description',''),
                      1 if request.form.get('is_organic') else 0,
                      float(request.form.get('min_order',1)),
                      request.form.get('emoji', emoji_map.get(cat,'🌾'))))
        conn.commit()
        conn.close()
        flash('Crop listed successfully! 🌾 Customers can now see it.', 'success')
        return redirect(url_for('farmer_dashboard'))
    return render_template('add_crop.html')

@app.route('/farmer/crop/edit/<int:crop_id>', methods=['GET','POST'])
@farmer_required
def edit_crop(crop_id):
    conn = get_db()
    crop = conn.execute("SELECT * FROM crops WHERE id=? AND farmer_id=?",
                        (crop_id, session['user_id'])).fetchone()
    if not crop:
        flash('Crop not found.', 'danger')
        return redirect(url_for('farmer_dashboard'))
    if request.method == 'POST':
        conn.execute("""UPDATE crops SET name=?,category=?,quantity=?,price=?,unit=?,
                        harvest_date=?,location=?,description=?,is_organic=?,min_order=?,status=?
                        WHERE id=? AND farmer_id=?""",
                     (request.form['name'], request.form['category'],
                      float(request.form['quantity']), float(request.form['price']),
                      request.form.get('unit','kg'), request.form.get('harvest_date',''),
                      request.form.get('location',''), request.form.get('description',''),
                      1 if request.form.get('is_organic') else 0,
                      float(request.form.get('min_order',1)),
                      request.form.get('status','active'),
                      crop_id, session['user_id']))
        conn.commit()
        conn.close()
        flash('Listing updated!', 'success')
        return redirect(url_for('farmer_dashboard'))
    conn.close()
    return render_template('edit_crop.html', crop=crop)

@app.route('/farmer/crop/delete/<int:crop_id>')
@farmer_required
def delete_crop(crop_id):
    conn = get_db()
    conn.execute("DELETE FROM crops WHERE id=? AND farmer_id=?", (crop_id, session['user_id']))
    conn.commit()
    conn.close()
    flash('Listing removed.', 'success')
    return redirect(url_for('farmer_dashboard'))

@app.route('/farmer/order/update/<int:order_id>', methods=['POST'])
@farmer_required
def update_order_status(order_id):
    status = request.form.get('status')
    conn = get_db()
    conn.execute("UPDATE orders SET status=? WHERE id=? AND farmer_id=?",
                 (status, order_id, session['user_id']))
    conn.commit()
    conn.close()
    flash(f'Order status updated to {status}.', 'success')
    return redirect(url_for('farmer_dashboard'))

@app.route('/farmer/profile', methods=['GET','POST'])
@farmer_required
def farmer_profile():
    conn = get_db()
    if request.method == 'POST':
        conn.execute("""UPDATE users SET name=?,location=?,district=?,language=?,bank_account=?,ifsc=?
                        WHERE id=?""",
                     (request.form['name'], request.form['location'],
                      request.form['district'], request.form.get('language','English'),
                      request.form.get('bank_account',''), request.form.get('ifsc',''),
                      session['user_id']))
        conn.commit()
        session['name'] = request.form['name']
        flash('Profile updated!', 'success')
    user = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    conn.close()
    return render_template('farmer_profile.html', user=user)

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
