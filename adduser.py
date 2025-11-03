import psycopg2
import psycopg2.extras
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

# -------------------------
# DATABASE CONFIGURATION
# -------------------------
RDS_HOST = 'mp-database.c5iswawek3lu.ap-south-1.rds.amazonaws.com'
RDS_PORT = 5432
RDS_DBNAME = 'postgres'
RDS_USER = 'postgres'
RDS_PASSWORD = 'postgres123'

# -------------------------
# FLASK SETUP
# -------------------------
app = Flask(__name__)
CORS(app)

# -------------------------
# DATABASE CONNECTION
# -------------------------
def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=RDS_HOST,
            port=RDS_PORT,
            database=RDS_DBNAME,
            user=RDS_USER,
            password=RDS_PASSWORD
        )
        return conn
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return None

# -------------------------
# ROUTE 1: Serve adduser.html UI
# -------------------------
@app.route('/')
def serve_add_user_ui():
    # strictly render adduser.html from templates
    return render_template('adduser.html')

# -------------------------
# ROUTE 2: Add user API
# -------------------------
@app.route('/add-user', methods=['POST'])
def add_user():
    data = request.json
    username = data.get('username')
    canonical_id = data.get('canonical_id')

    if not username or not canonical_id:
        return jsonify({"success": False, "message": "Both username and canonical ID are required."}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"success": False, "message": "Database connection failed."}), 500

    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO s3_users (username, canonical_id) VALUES (%s, %s)",
            (username, canonical_id)
        )
        conn.commit()
        cur.close()
        return jsonify({"success": True, "message": f"User '{username}' added successfully!"}), 200
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return jsonify({"success": False, "message": "Username or Canonical ID already exists."}), 409
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()

# -------------------------
# ROUTE 3: View all users API
# -------------------------
@app.route('/view-users', methods=['GET'])
def view_users():
    conn = get_db_connection()
    if not conn:
        return jsonify({"success": False, "message": "Database connection failed."}), 500

    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT username, canonical_id FROM s3_users ORDER BY username ASC")
        rows = cur.fetchall()
        users = [dict(row) for row in rows]
        cur.close()
        return jsonify({"success": True, "users": users}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()

# -------------------------
# RUN FLASK
# -------------------------
@app.route('/adduser')
def serve_add_user_ui():
    """Serve the main app.html file."""
    return render_template('adduser.html')
if __name__ == '__main__':
    app.run(debug=True)
