from flask import Flask, request, render_template, jsonify, session, redirect, url_for
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, FileField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length
import firebase_admin
from firebase_admin import credentials, firestore, storage ,db
import bcrypt
from flask_limiter import Limiter
from flask_wtf.csrf import CSRFProtect 
from functools import wraps
from flask_cors import CORS
from dotenv import load_dotenv
import os
import math
import json
import logging

logging.basicConfig(level=logging.INFO)

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

csrf = CSRFProtect(app)
limiter = Limiter(app)
CORS(app)

service_account_info = json.loads(os.getenv('FIREBASE_CREDENTIALS_JSON'))

# Initialize Firebase Admin SDK
cred = credentials.Certificate(service_account_info)
firebase_admin.initialize_app(cred,{
    'databaseURL': "https://tunnel-ac8de-default-rtdb.firebaseio.com/"
})

# Initialize Firestore and Storage
db = firestore.client()
bucket = storage.bucket('tunnel-ac8de.appspot.com')  # Set Firebase storage bucket here


# Helper function for password encryption
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

# Create a registration form class
class RegistrationForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired()])
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=25)])
    email = StringField('Email ID', validators=[DataRequired()])
    aadhar = StringField('Aadhar No', validators=[DataRequired(), Length(max=12)])
    locopilotid = StringField('Locopilot ID', validators=[DataRequired()])
    govtID = FileField('Upload Government ID', validators=[DataRequired()])
    region = SelectField('Region', choices=[('south', 'South'), ('north', 'North')], validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Register')

# Define the login form
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    aadhar_no = StringField('Aadhaar Number', validators=[DataRequired(), Length(min=12, max=12)])  # Validate Aadhaar number length
    submit = SubmitField('Login')

# Route for the root page
@app.route('/')
def index():
    return redirect(url_for('register'))

@app.route('/operation')
def operation():
    # Retrieve userID and tunnelID from the query parameters
    user_id = request.args.get('userID')
    tunnel_id = request.args.get('tunnelID')
    tunnelName=request.args.get('tunnelName')
    length=request.args.get('length')
    geofence=request.args.get('geofence')
    geofence_r=request.args.get('geofence_r')

    if not user_id or not tunnel_id:
        # Redirect to an error page or return a friendly error message
        return render_template('error.html', message="User ID and Tunnel ID are required"), 400

    # Pass userID and tunnelID to the template
    return render_template('operation.html', user_id=user_id, tunnel_id=tunnel_id, tunnelName=tunnelName, length=length, geofence=geofence, geofence_r=geofence_r)

@app.route('/home')
def home():
    user_id = session.get('user_id') 
    return render_template('home.html',user_id=user_id)

# Route to render the registration page
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    notification_message = None  # Initialize notification_message
    if form.validate_on_submit():
        # Get form data
        name = form.name.data
        username = form.username.data
        email = form.email.data
        aadhar = form.aadhar.data
        locopilotid = form.locopilotid.data
        region = form.region.data
        password = form.password.data
        govtID = form.govtID.data

        # Check if email, aadhar, or locopilotid already exist in the database
        existing_user = db.collection('user').where('email', '==', email).get()
        existing_aadhar = db.collection('user').where('aadhar_no', '==', aadhar).get()
        existing_locopilotid = db.collection('user').where('locopilotid', '==', locopilotid).get()

        if existing_user:
            notification_message = "User already exists, please try again."
            return render_template('registration.html', form=form, notification_message=notification_message)

        if existing_aadhar:
            notification_message = "Aadhar number already exists, please try again."
            return render_template('registration.html', form=form, notification_message=notification_message)

        if existing_locopilotid:
            notification_message = "Locopilot ID already exists, please try again."
            return render_template('registration.html', form=form, notification_message=notification_message)

        # Password hashing
        hashed_password = hash_password(password)

        # Upload Government ID to Firebase Storage
        file_extension = govtID.filename.split('.')[-1]  # Get the original file extension
        blob = bucket.blob(f'govt_ids/{locopilotid}.{file_extension}')  # Use Locopilot ID for uniqueness
        blob.upload_from_file(govtID, content_type=govtID.content_type)  # Set the content type
        blob.make_public()  # Make the file publicly accessible
        govtID_url = blob.public_url  # Get downloadable URL

        # Store user data in Firestore with "unverified" status
        user_data = {
            'name': name,
            'username': username,
            'email': email,
            'aadhar_no': aadhar,
            'locopilotid': locopilotid,
            'region': region,
            'password': hashed_password.decode('utf-8'),
            'status': 'Unverified',
            'document': govtID_url  # Save the URL in Firestore
        }
        db.collection('user').add(user_data)

        # Set a success message in the session
        notification_message = "Registration successful, awaiting verification! We will inform you very soon."
        return render_template('registration.html', form=form, notification_message=notification_message)

    return render_template('registration.html', form=form, notification_message=notification_message)



# Route to render the login page
# Route to render the login page
@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    notification_message = None  # Initialize notification message
    form = LoginForm()  # Create an instance of the login form

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        aadhar_no = form.aadhar_no.data

        # Fetch user from Firestore
        user_ref = db.collection('user').where('username', '==', username).where('aadhar_no', '==', aadhar_no).limit(1).stream()
        user_data = None
        user_id = None  # Initialize variable to store user_id

        # Loop through the Firestore documents (should be only one due to the limit(1) clause)
        for doc in user_ref:
            user_data = doc.to_dict()
            user_id = doc.id  # Store the Firestore document ID (user_id)

        # Validate user credentials
        if user_data and bcrypt.checkpw(password.encode('utf-8'), user_data['password'].encode('utf-8')):
            if user_data['status'] == 'Verified':
                # Store the username and user_id in session
                session['username'] = username
                session['user_id'] = user_id  # Store the Firestore document ID in session
                
                notification_message = "Login successful! Welcome back!"
                return redirect('/home')  # Redirect to home page or another page after successful login
            else:
                notification_message = "Account not verified. Please check your email."
        else:
            notification_message = "Invalid username, password, or Aadhaar number."

    return render_template('login.html', form=form, notification_message=notification_message)

#logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# HOME Page routes and functions

# Haversine formula to calculate the distance between two points (latitude and longitude)
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371000  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = R * c  # Distance in meters
    return distance

# Check geofence and update tunnel status
def check_geofence(user_location, train_status, tunnels):
    sorted_tunnels = []
    tunnel_distances = []
    notifications = []

    # Loop through all tunnels and calculate distances
    for tunnel in tunnels:
        geofence = tunnel.get('geofence', [])

        radius = int(tunnel.get('geofence_Radius', [0])[0])
        print(f"Tunnel location: {geofence} , Tunnel Radius : {radius}")

        if geofence:
            coordinates_str = geofence[0]
            try:
                tunnel_lat, tunnel_lon = map(float, coordinates_str.split(','))

                # Calculate distance from the user's location to the geofence's border
                distance_to_border = calculate_distance(
                    user_location['lat'], user_location['lon'],
                    tunnel_lat, tunnel_lon
                ) / 1000  # Convert to KM

                tunnel_distances.append({
                    'tunnel': tunnel,
                    'distance_to_geofence_border': distance_to_border,
                    'train_status': train_status,
                    'geofence':geofence,
                    'radius':radius
                })

                # Notification for close tunnels
                if distance_to_border <= radius:
                    notifications.append({
                        'title': f"Tunnel {tunnel['name']} Nearby",
                        'message': f"You are close to {tunnel['name']}! Estimated distance: {distance_to_border:.2f} KM"
                    })
            except ValueError:
                logging.error("Error parsing geofence coordinates for tunnel:", tunnel['name'])
        else:
            logging.error("Tunnel does not have a geofence:", tunnel['name'])

    # Sort tunnels by proximity to the geofence border
    sorted_tunnels = sorted(tunnel_distances, key=lambda x: x['distance_to_geofence_border'])

    return sorted_tunnels, notifications

@app.route('/get_tunnels', methods=['POST'])
def get_tunnels():
    try:
        user_location = request.get_json()
        user_lat = user_location.get('user_lat')
        user_lon = user_location.get('user_lon')

        if not user_lat or not user_lon:
            return jsonify({'error': 'User location not provided'}), 400

        # Fetch tunnels from Firebase Firestore
        tunnels_ref = db.collection('tunnels').stream()
        
        # Prepare tunnels with clear ID access
        tunnels = []
        # Attach the tunnel document ID to the tunnel data
        for tunnel in tunnels_ref:
            tunnel_data = tunnel.to_dict()
            tunnel_data['id'] = tunnel.id
            
            # Extract the radius from the tunnel data (e.g., from 'geofence_Radius')
            radius = tunnel_data.get('geofence_Radius', [0])[0]  # Assuming geofence_Radius is a list
            tunnel_data['radius'] = radius  # Add radius to tunnel data
            
            tunnels.append(tunnel_data)

        # Fetch train status (from session or DB)
        train_status = int(session.get('train_status', 0))

        # Check geofence and get sorted tunnel data
        sorted_tunnels, notifications = check_geofence(
            {'lat': user_lat, 'lon': user_lon},
            train_status,
            tunnels
        )

        return jsonify({
            'tunnels': sorted_tunnels,  # Ensure this is an array of tunnel objects
            'notifications': notifications
        })

    except Exception as e:
        logging.error(f"Error retrieving tunnels: {e}")
        return jsonify({'error': 'Failed to retrieve tunnels'}), 500

#user detail route
@app.route('/get_user_details', methods=['POST'])
@csrf.exempt  # Disable CSRF protection for this route
def get_user_details():
    try:
        # Assume user_id is stored in the session
        user_id = session.get('user_id')

        if not user_id:
            return jsonify({'error': 'User not logged in'}), 401

        # Fetch the user details from Firestore
        user_ref = db.collection('user').document(user_id)
        user_doc = user_ref.get()

        if user_doc.exists:
            user_data = user_doc.to_dict()
            user_details = {
                'name': user_data.get('name', 'Unknown'),
                'username': user_data.get('username', 'Unknown'),
                'email': user_data.get('email', 'Unknown'),
                'locopilotid': user_data.get('locopilotid', 'Unknown'),
                'train_status': user_data.get('train_status', 0)  # Default to 'normal' if not present
            }
            return jsonify(user_details)
        else:
            return jsonify({'error': 'User not found'}), 404

    except Exception as e:
        logging.error(f"Error fetching user details: {e}")
        return jsonify({'error': 'Failed to fetch user details'}), 500
    
def update_train_status(user_id, tunnel_id, distance, geofence_radius):
    # Reference to the tunnel in the database
    radius=geofence_radius/1000
    tunnel_ref = firebase_admin.db.reference(f'/{tunnel_id}')
    tunnel_data = tunnel_ref.get()

    # If the tunnel does not exist, initialize it
    if tunnel_data is None:
        tunnel_data = {
            'status': 'OFF',
            'train_cnt': 0
        }
        tunnel_ref.set(tunnel_data)  # Create the tunnel with default values
        print(f"Initialized tunnel {tunnel_id} with default values.")

    # Retrieve current status and user data
    current_status = tunnel_data.get('status', 'OFF')
    user_previous_status = tunnel_data.get(user_id, 0)
    train_cnt = tunnel_data.get('train_cnt', 0)

    if distance <= radius:
        # User is inside the geofence
        if current_status == 'OFF' or user_previous_status == 0:
            # Turn ON the train status
            new_status = 'ON'
            train_cnt += 1
            user_status = 1
        else:
            # User already turned ON the status
            return {'message': 'User has already turned ON the train status.'}
    else:
        # User is outside the geofence
        if current_status == 'ON' and user_previous_status == 1:
            if train_cnt == 1:
                # Last user turning OFF the train status
                new_status = 'OFF'
                train_cnt = 0
            else:
                # Decrease train count, keep status ON
                new_status = 'ON'
                train_cnt -= 1
            user_status = 0
        else:
            # User already turned OFF the status
            return {'message': 'User has already turned OFF the train status.'}

    # Update the tunnel data with the new status and train count
    tunnel_ref.update({
        'status': new_status,
        'train_cnt': train_cnt,
        f'{user_id}': user_status
    })

    return {'message': f'Train status updated to {new_status}, train count: {train_cnt}.'}


# Route to check train status based on user input
@app.route('/check-train-status', methods=['POST'])
def check_train_status():
    data = request.json
    user_id = data.get('userId')
    tunnel_id = data.get('tunnelId')
    distance = float(data.get('distanceBetweenUserAndGeofence'))
    radius = data.get('radius')

    try:
        # Log input data for debugging
        print(f"Received data: user_id={user_id}, tunnel_id={tunnel_id}, distance={distance} Km, radius={radius/1000} Km")

        result = update_train_status(user_id, tunnel_id, distance, radius)
        return jsonify(result), 200
    except Exception as e:
        print(f"Error updating train status: {e}")
        return jsonify({'message': f'Internal Server Error: {str(e)}'}), 500
    

# Operation page route

@app.route('/operation/fetch-tunnel-data', methods=['POST'])
def fetch_tunnel_data():
    data = request.json
    tunnel_id = data.get('tunnelID')
    

    if not tunnel_id:
        return jsonify({'success': False, 'message': 'Tunnel ID is required.'}), 400

    try:
        # Fetch data from Firebase Realtime Database
        tunnel_ref = firebase_admin.db.reference(f'/{tunnel_id}')
        tunnel_data = tunnel_ref.get()

        if not tunnel_data:
            return jsonify({'success': False, 'message': 'Tunnel not found.'}), 404

        return jsonify({
            'success': True,
            'status': tunnel_data.get('status', 'OFF'),
            'train_cnt': tunnel_data.get('train_cnt', 0)
        }), 200
    except Exception as e:
        print(f"Error fetching tunnel data: {e}")
        return jsonify({'success': False, 'message': f'Internal Server Error: {str(e)}'}), 500
    
def update_manual_status(user_id, tunnel_id, action):
    # Reference to the tunnel in the database
    tunnel_ref = firebase_admin.db.reference(f'/{tunnel_id}')
    tunnel_data = tunnel_ref.get()

    # If the tunnel does not exist, return an error
    if tunnel_data is None:
        return {'success': False, 'message': 'Tunnel does not exist.'}

    # Fetch the current status and train count
    current_status = tunnel_data.get('status', 'OFF')
    train_cnt = tunnel_data.get('train_cnt', 0)
    

    # Validate user input and toggle the status
    if action == 'ON':
        if current_status == 'ON':
            return {'success': False, 'message': 'Light is already ON.'}
        new_status = 'ON'
        train_cnt += 1
    elif action == 'OFF':
        if current_status == 'OFF':
            return {'success': False, 'message': 'Light is already OFF.'}
        new_status = 'OFF'
        train_cnt = max(train_cnt - 1, 0)  # Ensure train count doesn't go negative
    else:
        return {'success': False, 'message': 'Invalid action. Use "ON" or "OFF".'}

    # Update the database
    tunnel_ref.update({
        'status': new_status,
        'train_cnt': train_cnt
    })

    return {'success': True, 'message': f'Light status updated to {new_status}. Train count: {train_cnt}'}

@app.route('/operation/manual-operation', methods=['POST'])
def manual_operation():
    data = request.json
    user_id = data.get('userID')
    tunnel_id = data.get('tunnelID')
    action = data.get('action')  # ON or OFF

    # Validate input
    if not user_id or not tunnel_id or not action:
        return jsonify({'success': False, 'message': 'Missing required parameters.'}), 400

    try:
        # Update the status manually
        result = update_manual_status(user_id, tunnel_id, action)
        return jsonify(result), 200 if result['success'] else 400
    except Exception as e:
        print(f"Error in manual operation: {e}")
        return jsonify({'success': False, 'message': f'Internal Server Error: {str(e)}'}), 500


# sos request 

@app.route('/sos/submit', methods=['POST'])
def submit_sos_request():
    notification_message = None  # Initialize notification message
    
    # Check if the incoming request is a POST request
    if request.method == 'POST':
        # Extract data from the JSON payload (assuming the request body contains JSON data)
        data = request.get_json()

        # Validate required fields
        required_fields = ['issue', 'issueType', 'tunnelID', 'tunnelName', 
                           'locopilotID', 'lastLocation', 
                           'requestTime', 'status']

        # Check if all required fields are present in the request data
        for field in required_fields:
            if field not in data:
                notification_message = f"Missing field: {field}"
                return jsonify({"success": False, "message": notification_message}), 400

        # Ensure lastLocation is a valid array
        if not isinstance(data['lastLocation'], list):
            notification_message = "Invalid data type for lastLocation. Must be an array."
            return jsonify({"success": False, "message": notification_message}), 400

        # If all required fields are present, we proceed to store the request in Firestore
        sos_data = {
            'description': data['issue'],
            'issueType': data['issueType'],
            'tunnelId': data['tunnelID'],
            'tunnelName': data['tunnelName'],
            'locopilotId': data['locopilotID'],
            'lastLocation': data['lastLocation'],  # Save the location array
            'status': data['status'],
            'trainId':"111",
            'locopilotName':"Karan Jadhav",
            'requestTime': firestore.SERVER_TIMESTAMP  # Optionally add a timestamp
        }

        # Store the SOS request data in Firestore under the 'sos_requests' collection
        try:
            db.collection('sos_requests').add(sos_data)
            notification_message = "SOS request submitted successfully!"
            return jsonify({"success": True, "message": notification_message}), 200
        except Exception as e:
            notification_message = f"Error submitting SOS request: {str(e)}"
            return jsonify({"success": False, "message": notification_message}), 500

    # If the request is not a POST request, return an error
    return jsonify({"success": False, "message": "Invalid request method."}), 405




if __name__ == '__main__':
    app.run(ssl_context='adhoc')
