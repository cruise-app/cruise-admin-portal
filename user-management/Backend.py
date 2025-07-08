import os
from flask import Flask, request, jsonify, render_template # ensure render_template is imported
from pymongo import MongoClient
from bson.objectid import ObjectId
from flask_cors import CORS
from urllib.parse import quote_plus
from datetime import datetime
import time
import json
from json import JSONEncoder

# Custom JSON encoder to handle ObjectId
class MongoJSONEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d')
        return super().default(obj)

app = Flask(__name__)
CORS(app) # Enable CORS for frontend communication

# Configure Flask to use the custom JSON encoder
app.json_encoder = MongoJSONEncoder

# Add this after the app = Flask(__name__) line
@app.before_request
def check_db_connection():
    """Middleware to ensure database connection is active before processing requests."""
    if request.endpoint != 'static':  # Skip check for static files
        if not db_connection_successful or global_users_collection is None:
            print("WARNING: Database connection lost. Attempting to reconnect...")
            if not init_db_connection():
                return jsonify({
                    "success": False,
                    "error": "Database connection unavailable"
                }), 503  # Service Unavailable

# MongoDB Configuration - REPLACE WITH YOUR ACTUAL CREDENTIALS IF DIFFERENT
# Ensure these match the credentials for your MongoDB Atlas cluster user
username = "Nour2003"
password = "Nour2003"
cluster_url = "cluster0.rgfcr8x.mongodb.net" # Your MongoDB Atlas cluster URL

# URL encode credentials for safe inclusion in connection string
escaped_username = quote_plus(username)
escaped_password = quote_plus(password)

# Construct the full MongoDB Atlas connection string
connection_string = f"mongodb+srv://{escaped_username}:{escaped_password}@{cluster_url}/CruiseDB?retryWrites=true&w=majority"

# Global variable to store the users collection.
# It will be initialized once on application startup.
global_users_collection = None
# Add a flag to indicate if DB connection was successful
db_connection_successful = False

def init_db_connection():
    """
    Establishes and returns a connection to the MongoDB 'users' collection.
    Includes retry logic for more robust connection handling.
    This function will be called once on app startup.
    """
    global global_users_collection
    global db_connection_successful

    # If connection already established and flagged as successful, do nothing
    if db_connection_successful and global_users_collection is not None:
        print("MongoDB connection already established and confirmed, skipping re-initialization.")
        return True

    max_retries = 5
    retry_delay = 3

    for attempt in range(max_retries):
        try:
            print(f"Attempting MongoDB connection... (Attempt {attempt + 1}/{max_retries})")
            # Create a new client instance
            client = MongoClient(
                connection_string,
                serverSelectionTimeoutMS=5000,  # 5 second timeout for server selection
                connectTimeoutMS=10000,  # 10 second timeout for initial connection
                socketTimeoutMS=10000,  # 10 second timeout for socket operations
            )
            
            # Test the connection
            client.admin.command('ping')
            print("MongoDB ping successful.")
            
            # Get database and collection
            db = client.CruiseDB
            users_collection = db.users
            
            # Verify collection access with a test operation
            test_count = users_collection.count_documents({})
            print(f"Successfully connected to MongoDB. Found {test_count} documents in users collection.")
            
            # Only set global variables if all tests pass
            global_users_collection = users_collection
            db_connection_successful = True
            
            return True

        except Exception as e:
            print(f"MongoDB connection attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("Failed to establish MongoDB connection after all retries.")
                global_users_collection = None
                db_connection_successful = False
                return False

    return False

# --- NEW: Route to serve the frontend HTML (correctly indented) ---
@app.route('/onemore.html')
def serve_onemore_html():
    return render_template('onemore.html')

# NEW: Optional root route to serve the same HTML for convenience
@app.route('/')
def serve_root_html():
    return render_template('onemore.html')
# --- END NEW ROUTES ---


@app.route('/api/users/count', methods=['GET'])
def get_user_count():
    """Returns the total number of users in the collection."""
    # Check the flag for clearer status
    if not db_connection_successful or global_users_collection is None:
        print("ERROR (get_user_count): Database connection not active.")
        return jsonify({
            "success": False,
            "error": "Database connection not established"
        }), 500

    try:
        user_count = global_users_collection.count_documents({})
        return jsonify({
            "success": True,
            "count": user_count
        }), 200
    except Exception as e:
        print(f"ERROR (get_user_count): Exception during user count fetch: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# === THIS IS THE CRITICAL FIX: The @app.route decorator for the main get_users function ===
@app.route('/api/users', methods=['GET'])
def get_users():
    """
    Fetches all user documents from the 'users' collection and returns them as JSON.
    Returns in the format expected by DataTables.
    """
    if not db_connection_successful or global_users_collection is None:
        print("ERROR (get_users): Database connection not active.")
        return jsonify({
            "draw": 1,
            "recordsTotal": 0,
            "recordsFiltered": 0,
            "data": [],
            "error": "Database connection not established"
        }), 500

    try:
        print("DEBUG (get_users): Attempting to fetch users...")
        # Get total count for recordsTotal
        total_count = global_users_collection.count_documents({})
        print(f"DEBUG (get_users): Total count in collection: {total_count}")

        # Fetch all users
        users_cursor = global_users_collection.find({})
        users_list = []
        
        for user in users_cursor:
            # Convert MongoDB ObjectId to string
            user_id = str(user.get('_id', ''))
            
            # Handle date formatting
            date_of_birth = user.get('dateOfBirth')
            if isinstance(date_of_birth, datetime):
                date_of_birth = date_of_birth.strftime('%Y-%m-%d')
            elif isinstance(date_of_birth, str):
                date_of_birth = date_of_birth.split('T')[0]
            else:
                date_of_birth = ''

            formatted_user = {
                'id': user_id,
                'firstName': user.get('firstName', ''),
                'lastName': user.get('lastName', ''),
                'username': user.get('userName', ''),
                'email': user.get('email', ''),
                'phone': user.get('phoneNumber', ''),
                'gender': user.get('gender', ''),
                'dateOfBirth': date_of_birth,
                'status': user.get('status', 'active')
            }
            users_list.append(formatted_user)

        print(f"DEBUG (get_users): Successfully retrieved {len(users_list)} users")
        
        response_data = {
            "draw": int(request.args.get('draw', 1)),
            "recordsTotal": total_count,
            "recordsFiltered": len(users_list),
            "data": users_list
        }
        
        print(f"DEBUG (get_users): Sending response with {len(users_list)} users")
        return jsonify(response_data), 200

    except Exception as e:
        print(f"ERROR (get_users): {str(e)}")
        return jsonify({
            "draw": 1,
            "recordsTotal": 0,
            "recordsFiltered": 0,
            "data": [],
            "error": str(e)
        }), 500

@app.route('/api/users', methods=['POST'])
def create_user():
    """Creates a new user document in the 'users' collection."""
    if not db_connection_successful or global_users_collection is None:
        print("ERROR (create_user): Database connection not active.")
        return jsonify({
            "success": False,
            "error": "Database connection not established"
        }), 500

    try:
        print("DEBUG (create_user): Received POST request to create user")
        new_user_data = request.get_json()
        
        if not new_user_data:
            print("ERROR (create_user): No data provided in request")
            return jsonify({"success": False, "error": "No data provided"}), 400

        print(f"DEBUG (create_user): Received data: {new_user_data}")

        # Validate required fields
        required_fields = ['firstName', 'lastName', 'username', 'email']
        missing_fields = [field for field in required_fields if not new_user_data.get(field)]
        if missing_fields:
            error_msg = f"Missing required fields: {', '.join(missing_fields)}"
            print(f"ERROR (create_user): {error_msg}")
            return jsonify({"success": False, "error": error_msg}), 400

        # Create user document with proper field mapping
        user_document = {
            'firstName': new_user_data['firstName'].strip(),
            'lastName': new_user_data['lastName'].strip(),
            'userName': new_user_data['username'].strip(),  # Map username to userName
            'email': new_user_data['email'].strip(),
            'phoneNumber': new_user_data.get('phone', '').strip(),  # Map phone to phoneNumber
            'gender': new_user_data.get('gender', '').strip(),
            'status': new_user_data.get('status', 'active').strip(),
            'createdAt': datetime.utcnow(),
            'updatedAt': datetime.utcnow()
        }

        # Handle date of birth if provided
        if 'dateOfBirth' in new_user_data and new_user_data['dateOfBirth']:
            try:
                # Store as datetime object
                user_document['dateOfBirth'] = datetime.strptime(new_user_data['dateOfBirth'].strip(), '%Y-%m-%d')
            except ValueError as e:
                print(f"ERROR (create_user): Invalid date format: {e}")
                return jsonify({
                    "success": False,
                    "error": "Invalid dateOfBirth format. Use YYYY-MM-DD format."
                }), 400

        print(f"DEBUG (create_user): Attempting to insert document: {user_document}")
        
        # Check if username already exists
        existing_user = global_users_collection.find_one({'userName': user_document['userName']})
        if existing_user:
            print(f"ERROR (create_user): Username {user_document['userName']} already exists")
            return jsonify({
                "success": False,
                "error": "Username already exists"
            }), 409

        # Check if email already exists
        existing_user = global_users_collection.find_one({'email': user_document['email']})
        if existing_user:
            print(f"ERROR (create_user): Email {user_document['email']} already exists")
            return jsonify({
                "success": False,
                "error": "Email already exists"
            }), 409

        result = global_users_collection.insert_one(user_document)
        
        if result and result.inserted_id:
            print(f"DEBUG (create_user): Successfully created user with ID: {result.inserted_id}")
            
            # Get the complete user document from the database
            created_user = global_users_collection.find_one({'_id': result.inserted_id})
            if not created_user:
                return jsonify({
                    "success": False,
                    "error": "User created but could not be retrieved"
                }), 500

            # Format the response data
            response_data = {
                'id': str(created_user['_id']),
                'firstName': created_user['firstName'],
                'lastName': created_user['lastName'],
                'username': created_user['userName'],
                'email': created_user['email'],
                'phone': created_user.get('phoneNumber', ''),
                'gender': created_user.get('gender', ''),
                'status': created_user.get('status', 'active'),
                'dateOfBirth': created_user['dateOfBirth'].strftime('%Y-%m-%d') if created_user.get('dateOfBirth') else ''
            }
            
            return jsonify({
                "success": True,
                "message": "User created successfully",
                "user": response_data
            }), 201
        else:
            print("ERROR (create_user): Failed to create user - no inserted_id returned")
            return jsonify({
                "success": False,
                "error": "Failed to create user"
            }), 500

    except Exception as e:
        print(f"ERROR (create_user): Exception during user creation: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/users/<user_id>', methods=['PUT'])
def update_user(user_id):
    """Updates an existing user document in the 'users' collection."""
    # Check the flag for clearer status
    if not db_connection_successful or global_users_collection is None:
        print("ERROR (update_user): Database connection not active.")
        return jsonify({
            "success": False,
            "error": "Database connection not established"
        }), 500

    try:
        # Convert user_id string to MongoDB's ObjectId
        try:
            obj_id = ObjectId(user_id)
        except Exception:
            return jsonify({"success": False, "error": "Invalid user ID format"}), 400

        user_updates = request.get_json()
        if not user_updates:
            return jsonify({"success": False, "error": "No update data provided"}), 400

        # Prevent _id or id from being updated, as they are immutable or not intended for update
        user_updates.pop('_id', None)
        user_updates.pop('id', None)

        # Map frontend field names to database field names before updating
        if 'username' in user_updates:
            user_updates['userName'] = user_updates.pop('username')
        if 'phone' in user_updates:
            user_updates['phoneNumber'] = user_updates.pop('phone')

        # Handle dateOfBirth: convert string to datetime object if present
        if 'dateOfBirth' in user_updates:
            date_of_birth_val = user_updates['dateOfBirth']
            if date_of_birth_val:
                try:
                    user_updates['dateOfBirth'] = datetime.strptime(date_of_birth_val, '%Y-%m-%d')
                except ValueError:
                    return jsonify({
                        "success": False,
                        "error": "Invalid dateOfBirth format. Please use ISO 8601 (%Y-%m-%d)."
                    }), 400
            else:
                user_updates['dateOfBirth'] = None # Allow setting to None if empty string is passed

        user_updates['updatedAt'] = datetime.utcnow() # Update timestamp for modification

        # Perform the update operation
        result = global_users_collection.update_one(
            {'_id': obj_id}, # Query by MongoDB's ObjectId
            {'$set': user_updates} # Use $set to update specific fields
        )

        if result.matched_count == 0:
            return jsonify({
                "success": False,
                "error": "User not found"
            }), 404
        elif result.modified_count == 0:
            return jsonify({
                "success": True,
                "message": "No changes made to user" # Case where data sent is identical to existing
            }), 200
        else:
            return jsonify({
                "success": True,
                "message": "User updated successfully"
            }), 200

    except Exception as e:
        print(f"ERROR (update_user): Exception during user update: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/users/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Deletes a user document from the 'users' collection."""
    # Check the flag for clearer status
    if not db_connection_successful or global_users_collection is None:
        print("ERROR (delete_user): Database connection not active.")
        return jsonify({
            "success": False,
            "error": "Database connection not established"
        }), 500

    try:
        # Convert user_id string to MongoDB's ObjectId
        try:
            obj_id = ObjectId(user_id)
        except Exception:
            return jsonify({"success": False, "error": "Invalid user ID format"}), 400

        # Perform the delete operation
        result = global_users_collection.delete_one({'_id': obj_id})

        if result.deleted_count == 0:
            return jsonify({
                "success": False,
                "error": "User not found"
            }), 404
        else:
            return jsonify({
                "success": True,
                "message": "User deleted successfully"
            }), 200

    except Exception as e:
        print(f"ERROR (delete_user): Exception during user deletion: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/users/<user_id>', methods=['GET'])
def get_user(user_id):
    """Fetches a single user document from the 'users' collection."""
    if not db_connection_successful or global_users_collection is None:
        print("ERROR (get_user): Database connection not active.")
        return jsonify({
            "success": False,
            "error": "Database connection not established"
        }), 500

    try:
        # Convert user_id string to MongoDB's ObjectId
        try:
            obj_id = ObjectId(user_id)
        except Exception:
            return jsonify({"success": False, "error": "Invalid user ID format"}), 400

        # Find the user
        user = global_users_collection.find_one({'_id': obj_id})
        
        if not user:
            return jsonify({
                "success": False,
                "error": "User not found"
            }), 404

        # Format the user data
        formatted_user = {
            'id': str(user['_id']),
            'firstName': user.get('firstName', ''),
            'lastName': user.get('lastName', ''),
            'username': user.get('userName', ''),
            'email': user.get('email', ''),
            'phone': user.get('phoneNumber', ''),
            'gender': user.get('gender', ''),
            'status': user.get('status', 'active')
        }

        # Handle date formatting
        date_of_birth = user.get('dateOfBirth')
        if isinstance(date_of_birth, datetime):
            formatted_user['dateOfBirth'] = date_of_birth.strftime('%Y-%m-%d')
        elif isinstance(date_of_birth, str):
            formatted_user['dateOfBirth'] = date_of_birth.split('T')[0]
        else:
            formatted_user['dateOfBirth'] = ''

        return jsonify(formatted_user), 200

    except Exception as e:
        print(f"ERROR (get_user): Exception during user fetch: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == '__main__':
    # Initialize the database connection once when the Flask app is run
    print("Initializing MongoDB connection...")
    if init_db_connection():
        print("MongoDB connection confirmed. Starting Flask application.")
        app.run(debug=True, host='127.0.0.1', port=5001)
    else:
        print("Failed to establish MongoDB connection. Application will not start.")
        exit(1) 