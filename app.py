from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os
import json
from datetime import datetime

app = Flask(__name__)

DB_PATH = 'data/food_orders.db'

# Initialize database
def init_db():
    if not os.path.exists('data'):
        os.makedirs('data')

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Create orders table (include location_id if this is a fresh DB)
    c.execute('''CREATE TABLE IF NOT EXISTS orders
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  restaurant TEXT NOT NULL,
                  name TEXT NOT NULL,
                  student_id TEXT NOT NULL,
                  phone TEXT NOT NULL,
                  items TEXT NOT NULL,
                  total REAL NOT NULL,
                  status TEXT DEFAULT 'Received',
                  order_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  location_id INTEGER DEFAULT NULL)''')  # location_id added here

    # Create locations table (admin-managed)
    c.execute('''CREATE TABLE IF NOT EXISTS locations
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  short_code TEXT,
                  is_active INTEGER NOT NULL DEFAULT 1,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # In case older DB exists without location_id column, add it
    # (SQLite allows ALTER TABLE .. ADD COLUMN)
    c.execute("PRAGMA table_info(orders)")
    cols = [row[1] for row in c.fetchall()]  # second field is column name
    if 'location_id' not in cols:
        try:
            c.execute('ALTER TABLE orders ADD COLUMN location_id INTEGER DEFAULT NULL')
        except Exception:
            # In rare edge cases (very old SQLite) ignore — main flow still works
            pass

    conn.commit()
    conn.close()

# Restaurant data with logos (unchanged)
restaurants = {
    "main_canteen": {
        "name": "Nalambagam Canteen",
        "image": "klu_nalambagam.jpg",
        #"logo": "nalambagam_logo.png",
        "description": "Authentic South Indian cuisine with fresh ingredients and traditional flavors",
        "rating": 4.5,
        "delivery_time": "15-20 min",
        "menu": {
            "breakfast": {
                "Idli": 8,
                "Masala Dosa": 45,
                "Pongal": 35,
                "Vada": 8,
                "Poori Set": 30
            },
            "lunch": {
                "Veg Meals": 70,
                "Special Meals": 90,
                "Chapati": 15,
                "Chicken Fried Rice": 100,
                "Veg Fried Rice": 70,
                "Egg Fried Rice": 80,
                "Biryani": 110,
                "Plain Biryani": 90
            },
            "snacks": {
                "Samosa": 15,
                "Bonda": 20,
                "Sandwich": 35,
                "Pani Puri": 30,
                "Masala Puri": 40
            },
            "beverages": {
                "Tea": 10,
                "Coffee": 15,
                "Buttermilk": 20,
                "Fresh Juice": 35
            }
        }
    },
    "madurai_lee": {
        "name": "Madurai Lee Corner",
        "image": "madurai_lee_corner_logo.jpg",
        #"logo": "madurai_lee_logo.png",
        "description": "Modern cafe serving premium coffee, teas, and delicious snacks",
        "rating": 4.3,
        "delivery_time": "10-15 min",
        "menu": {
            "coffee": {
                "Filter Coffee": 25,
                "Cappuccino": 60,
                "Latte": 70,
                "Espresso": 50,
                "Americano": 55,
                "Mocha": 75
            },
            "tea": {
                "Regular Tea": 15,
                "Green Tea": 30,
                "Masala Chai": 25,
                "Herbal Tea": 35,
                "Lemon Tea": 30
            },
            "cold beverages": {
                "Cold Coffee": 65,
                "Milk Shake": 80,
                "Smoothie": 90,
                "Iced Tea": 45,
                "Fresh Juice": 60
            },
            "snacks": {
                "Veg Sandwich": 50,
                "Grilled Sandwich": 65,
                "Burger": 75,
                "Pizza Slice": 85,
                "Cake": 45,
                "Cookies": 30
            }
        }
    },
    "radha_krishna": {
        "name": "Radha Krishna",
        "image": "radha_krishna.jpg",
        #"logo": "vasu_cafe_logo.png",
        "description": "Multi-cuisine restaurant offering South Indian, North Indian, and Chinese dishes",
        "rating": 4.4,
        "delivery_time": "20-25 min",
        "menu": {
            "south indian": {
                "Ghee Roast Dosa": 65,
                "Onion Uttapam": 55,
                "Rava Dosa": 50,
                "Pesarattu": 45,
                "Set Dosa": 40
            },
            "north indian": {
                "Paneer Butter Masala": 120,
                "Chole Bhature": 80,
                "Dal Makhani": 90,
                "Naan": 25,
                "Roti": 15
            },
            "chinese": {
                "Noodles": 70,
                "Fried Rice": 65,
                "Manchurian": 85,
                "Spring Rolls": 60,
                "Schezwan Rice": 75
            },
            "beverages": {
                "Fresh Lime": 30,
                "Mint Mojito": 50,
                "Falooda": 80,
                "Badam Milk": 45,
                "Rose Milk": 35
            }
        }
    }
}

# Initialize the database when the app starts
init_db()

# Admin credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

@app.route('/')
def home():
    return render_template('index.html', restaurants=restaurants)

@app.route('/menu/<restaurant_id>')
def menu(restaurant_id):
    if restaurant_id in restaurants:
        # Fetch active locations from DB and pass to template
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT id, name, short_code, is_active FROM locations WHERE is_active = 1 ORDER BY name")
        loc_rows = c.fetchall()
        conn.close()

        locations = [{'id': r[0], 'name': r[1], 'short_code': r[2], 'is_active': r[3]} for r in loc_rows]

        return render_template('menu.html',
                               restaurant=restaurants[restaurant_id],
                               restaurant_id=restaurant_id,
                               locations=locations)
    return redirect(url_for('home'))

@app.route('/order/<restaurant_id>', methods=['POST'])
def order(restaurant_id):
    if restaurant_id in restaurants:
        # Get form data
        name = request.form.get('name')
        student_id = request.form.get('student_id')
        phone = request.form.get('phone')
        location_id = request.form.get('location_id')  # new field from menu.html
        items = {}
        total = 0

        # Validate location_id server-side
        if not location_id:
            # missing location
            return render_template('menu.html',
                                   restaurant=restaurants[restaurant_id],
                                   restaurant_id=restaurant_id,
                                   locations=get_active_locations(),
                                   error="Please select a delivery location (admin-approved).")

        try:
            location_id_int = int(location_id)
        except:
            return render_template('menu.html',
                                   restaurant=restaurants[restaurant_id],
                                   restaurant_id=restaurant_id,
                                   locations=get_active_locations(),
                                   error="Invalid delivery location selected.")

        # Check location exists and is active
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT id, name, is_active FROM locations WHERE id = ?", (location_id_int,))
        loc_row = c.fetchone()
        if not loc_row or loc_row[2] != 1:
            conn.close()
            return render_template('menu.html',
                                   restaurant=restaurants[restaurant_id],
                                   restaurant_id=restaurant_id,
                                   locations=get_active_locations(),
                                   error="Selected delivery location is not available.")
        location_name = loc_row[1]

        # Calculate order items and total
        for category in restaurants[restaurant_id]['menu']:
            for item, price in restaurants[restaurant_id]['menu'][category].items():
                quantity = request.form.get(f'{category}_{item}')
                if quantity and int(quantity) > 0:
                    items[item] = {
                        'quantity': int(quantity),
                        'price': price,
                        'subtotal': price * int(quantity)
                    }
                    total += price * int(quantity)

        # Save order to database
        if items:
            # Insert order with location_id
            c.execute('''INSERT INTO orders (restaurant, name, student_id, phone, items, total, location_id)
                         VALUES (?, ?, ?, ?, ?, ?, ?)''',
                      (restaurants[restaurant_id]['name'],
                       name,
                       student_id,
                       phone,
                       json.dumps(items),
                       total,
                       location_id_int))
            order_id = c.lastrowid
            conn.commit()
            conn.close()

            # Get the order data for confirmation page
            order_data = {
                'id': order_id,
                'restaurant': restaurants[restaurant_id]['name'],
                'restaurant_logo': restaurants[restaurant_id].get('logo', ''),
                'name': name,
                'student_id': student_id,
                'phone': phone,
                'order_items': items,
                'total': total,
                'status': 'Received',
                'order_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'location_id': location_id_int,
                'location_name': location_name
            }

            return render_template('order.html', order=order_data)

        # no items selected
        conn.close()
    return redirect(url_for('home'))

@app.route('/order_status')
def order_status():
    return render_template('order_status.html')

@app.route('/api/order_status', methods=['POST'])
def api_order_status():
    student_id = request.form.get('student_id')
    phone = request.form.get('phone')

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''SELECT * FROM orders WHERE student_id = ? AND phone = ?
                 ORDER BY order_time DESC''', (student_id, phone))

    orders = []
    for row in c.fetchall():
        try:
            if row[5]:
                order_items = json.loads(row[5])
            else:
                order_items = {}
        except:
            order_items = {}

        orders.append({
            'id': row[0],
            'restaurant': row[1],
            'name': row[2],
            'student_id': row[3],
            'phone': row[4],
            'order_items': order_items,
            'total': row[6],
            'status': row[7],
            'order_time': row[8],
            'location_id': row[9] if len(row) > 9 else None
        })

    conn.close()

    return render_template('order_status.html', orders=orders,
                          student_id=student_id, phone=phone)

# Helper to fetch active locations
def get_active_locations():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name, short_code, is_active FROM locations WHERE is_active = 1 ORDER BY name")
    loc_rows = c.fetchall()
    conn.close()
    return [{'id': r[0], 'name': r[1], 'short_code': r[2], 'is_active': r[3]} for r in loc_rows]

# Admin routes
@app.route('/admin')
def admin_login():
    return render_template('admin_login.html')

@app.route('/admin/dashboard', methods=['POST'])
def admin_dashboard():
    username = request.form.get('username')
    password = request.form.get('password')

    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()

            c.execute('''SELECT * FROM orders ORDER BY order_time DESC''')
            orders = []
            for row in c.fetchall():
                try:
                    if row[5]:
                        order_items = json.loads(row[5])
                    else:
                        order_items = {}
                except:
                    order_items = {}

                orders.append({
                    'id': row[0],
                    'restaurant': row[1],
                    'name': row[2],
                    'student_id': row[3],
                    'phone': row[4],
                    'order_items': order_items,
                    'total': row[6],
                    'status': row[7],
                    'order_time': row[8],
                    'location_id': row[9] if len(row) > 9 else None
                })

            # fetch all locations (for admin panel)
            c.execute("SELECT id, name, short_code, is_active FROM locations ORDER BY created_at DESC")
            loc_rows = c.fetchall()
            locations = [{'id': r[0], 'name': r[1], 'short_code': r[2], 'is_active': r[3]} for r in loc_rows]

            conn.close()
            return render_template('admin_dashboard.html', orders=orders, locations=locations)
        except Exception as e:
            return render_template('admin_login.html', error="Database error occurred")
    else:
        return render_template('admin_login.html', error="Invalid credentials")

@app.route('/admin/dashboard')
def admin_dashboard_redirect():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''SELECT * FROM orders ORDER BY order_time DESC''')
    orders = []
    for row in c.fetchall():
        try:
            if row[5]:
                order_items = json.loads(row[5])
            else:
                order_items = {}
        except:
            order_items = {}

        orders.append({
            'id': row[0],
            'restaurant': row[1],
            'name': row[2],
            'student_id': row[3],
            'phone': row[4],
            'order_items': order_items,
            'total': row[6],
            'status': row[7],
            'order_time': row[8],
            'location_id': row[9] if len(row) > 9 else None
        })

    # fetch all locations (for admin panel)
    c.execute("SELECT id, name, short_code, is_active FROM locations ORDER BY created_at DESC")
    loc_rows = c.fetchall()
    locations = [{'id': r[0], 'name': r[1], 'short_code': r[2], 'is_active': r[3]} for r in loc_rows]

    conn.close()
    return render_template('admin_dashboard.html', orders=orders, locations=locations)

@app.route('/admin/add_location', methods=['POST'])
def admin_add_location():
    name = request.form.get('name', '').strip()
    short_code = request.form.get('short_code', '').strip() or None

    if not name:
        return redirect(url_for('admin_dashboard_redirect'))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO locations (name, short_code, is_active) VALUES (?, ?, 1)", (name, short_code))
        conn.commit()
    except Exception:
        # ignore unique constraint or other DB errors silently for now
        pass
    finally:
        conn.close()

    return redirect(url_for('admin_dashboard_redirect'))

@app.route('/admin/location/<int:location_id>/toggle', methods=['POST'])
def admin_toggle_location(location_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # flip is_active: 1 -> 0, 0 -> 1
    c.execute("UPDATE locations SET is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END WHERE id = ?", (location_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_dashboard_redirect'))

@app.route('/admin/location/<int:location_id>/delete', methods=['POST'])
def admin_delete_location(location_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM locations WHERE id = ?", (location_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_dashboard_redirect'))

@app.route('/admin/update_status', methods=['POST'])
def update_order_status():
    order_id = request.form.get('order_id')
    new_status = request.form.get('status')

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''UPDATE orders SET status = ? WHERE id = ?''',
              (new_status, order_id))

    conn.commit()
    conn.close()

    return redirect(url_for('admin_dashboard_redirect'))

@app.route('/admin/delete_order', methods=['POST'])
def delete_order():
    order_id = request.form.get('order_id')

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''DELETE FROM orders WHERE id = ?''', (order_id,))

    conn.commit()
    conn.close()

    return redirect(url_for('admin_dashboard_redirect'))

if __name__ == '__main__':
    app.run(debug=True)
