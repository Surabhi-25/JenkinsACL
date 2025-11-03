import os
import json
import psycopg2
import psycopg2.extras
import boto3
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from botocore.exceptions import ClientError

# --- 1. CONFIGURATION ---
RDS_HOST = 'mp-database.c5iswawek3lu.ap-south-1.rds.amazonaws.com'
RDS_PORT = 5432
RDS_DBNAME = 'postgres'
RDS_USER = 'postgres'
RDS_PASSWORD = 'postgres123'
BUCKET_NAME = 'mpversion'

# --- 2. AWS S3 Client Setup ---
s3_client = boto3.client('s3')

# --- 3. Flask App Setup ---
app = Flask(__name__)
CORS(app)

# --- 4. Database Connection ---
def get_db_connection():
    """Connect to PostgreSQL RDS."""
    try:
        conn = psycopg2.connect(
            host=RDS_HOST,
            port=RDS_PORT,
            database=RDS_DBNAME,
            user=RDS_USER,
            password=RDS_PASSWORD,
            connect_timeout=10
        )
        return conn
    except Exception as e:
        print(f"Database connection failed: {e}")
        return None


# ----------------------------------------------------------------------
# Helper: Get Canonical ID by Username
# ----------------------------------------------------------------------
def get_canonical_id_by_username(username):
    """Fetch Canonical ID using username."""
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return None
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        query = "SELECT canonical_id FROM s3_users WHERE username = %s"
        cur.execute(query, (username,))
        result = cur.fetchone()
        cur.close()
        return result['canonical_id'] if result else None
    except Exception as e:
        print(f"Database lookup failed for user {username}: {e}")
        return None
    finally:
        if conn:
            conn.close()


# ----------------------------------------------------------------------
# Helper: Get Current Grants for a Recipient
# ----------------------------------------------------------------------
def get_current_recipient_grants(object_key, recipient_id):
    """Check recipient’s current ACL permissions."""
    try:
        current_acl = s3_client.get_object_acl(Bucket=BUCKET_NAME, Key=object_key)
        has_read = has_write = False
        for grant in current_acl.get('Grants', []):
            grantee = grant.get('Grantee')
            permission = grant.get('Permission')
            if grantee and grantee.get('ID') == recipient_id:
                if permission == 'READ':
                    has_read = True
                elif permission == 'WRITE':
                    has_write = True
        return {"has_read": has_read, "has_write": has_write}
    except ClientError as e:
        raise e


# ----------------------------------------------------------------------
# 5. Add User (POST)
# ----------------------------------------------------------------------
@app.route('/add-user', methods=['POST'])
def handle_user_creation():
    """Add new username + Canonical ID to DB."""
    data = request.json
    username = data.get('username')
    canonical_id = data.get('canonical_id')

    if not all([username, canonical_id]):
        return jsonify({"success": False, "message": "Missing Username or Canonical ID."}), 400

    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"success": False, "message": "Database connection failed."}), 500
        cur = conn.cursor()
        insert_query = "INSERT INTO s3_users (username, canonical_id) VALUES (%s, %s)"
        cur.execute(insert_query, (username, canonical_id))
        conn.commit()
        cur.close()
        print(f"Added user: {username}")
        return jsonify({"success": True, "message": f"User {username} added successfully."}), 200
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return jsonify({"success": False, "message": f"Username or Canonical ID already exists."}), 409
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"User creation failed: {e}")
        return jsonify({"success": False, "message": f"Error: {e}"}), 500
    finally:
        if conn:
            conn.close()


# ----------------------------------------------------------------------
# 6. View Users (GET)
# ----------------------------------------------------------------------
@app.route('/view-users', methods=['GET'])
def view_registered_users():
    """View all user mappings."""
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"success": False, "message": "Database connection failed."}), 500
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT username, canonical_id FROM s3_users ORDER BY username ASC")
        users = [dict(row) for row in cur.fetchall()]
        cur.close()
        return jsonify({"success": True, "total_users": len(users), "users": users}), 200
    except Exception as e:
        print(f"Failed to retrieve users: {e}")
        return jsonify({"success": False, "message": f"Error: {e}"}), 500
    finally:
        if conn:
            conn.close()


# ----------------------------------------------------------------------
# 7. ACL Grant/Revoke (POST)
# ----------------------------------------------------------------------
@app.route('/acl-action', methods=['POST'])
def handle_acl_action():
    """Grant or revoke ACL permissions."""
    data = request.json
    action = data.get('action')
    permission_type = data.get('permission')
    object_key = data.get('object_key')
    recipient_username = data.get('recipient_username')
    owner_id = data.get('owner_canonical_id')

    if not all([action, permission_type, object_key, recipient_username, owner_id]):
        return jsonify({"success": False, "message": "Missing required data."}), 400

    recipient_id = get_canonical_id_by_username(recipient_username)
    if not recipient_id:
        return jsonify({"success": False, "message": f"No Canonical ID found for {recipient_username}."}), 404

    print(f"Executing {action}_{permission_type} for {recipient_username} on {object_key}")
    acl_grant_param = {'GrantFullControl': f'id="{owner_id}"'}
    final_read = [f'id="{owner_id}"']
    final_write = [f'id="{owner_id}"']

    try:
        if action == 'GRANT':
            if permission_type in ['READ', 'BOTH']:
                final_read.append(f'id="{recipient_id}"')
            if permission_type in ['WRITE', 'BOTH']:
                final_write.append(f'id="{recipient_id}"')
            success_msg = f"Granted {permission_type} access to {recipient_username} on {object_key}"

        elif action == 'REVOKE':
            current = get_current_recipient_grants(object_key, recipient_id)
            if current['has_read'] and permission_type not in ['READ', 'BOTH']:
                final_read.append(f'id="{recipient_id}"')
            if current['has_write'] and permission_type not in ['WRITE', 'BOTH']:
                final_write.append(f'id="{recipient_id}"')
            success_msg = f"Revoked {permission_type} access from {recipient_username} on {object_key}"
        else:
            return jsonify({"success": False, "message": "Invalid action type."}), 400

        acl_grant_param['GrantRead'] = ",".join(final_read)
        acl_grant_param['GrantWrite'] = ",".join(final_write)
        s3_client.put_object_acl(Bucket=BUCKET_NAME, Key=object_key, **acl_grant_param)

        return jsonify({"success": True, "message": success_msg}), 200
    except ClientError as e:
        err = e.response['Error']['Code']
        print(f"ACL Error: {err}")
        return jsonify({"success": False, "message": f"AWS Error: {err}"}), 500


# ----------------------------------------------------------------------
# 8. Serve Frontend UI (app.html)
# ----------------------------------------------------------------------
@app.route('/')
def serve_main_ui():
    """Serve the main app.html file."""
    return render_template('app.html')


# ----------------------------------------------------------------------
# 9. Run Flask
# ----------------------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True)
