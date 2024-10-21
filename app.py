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
    return render_template('operation.html')

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
                    'train_status': train_status
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
    
# Function to update Firebase based on distance and geofence
def update_train_status(user_id, tunnel_id, distance, geofence_radius):
    # Check if the distance is within the geofence radius
    if distance <= geofence_radius:
        # Get the current tunnel data
        tunnel_ref = firebase_admin.db.reference(f'/{tunnel_id}')
        tunnel_data = tunnel_ref.get()

        # Check the current status and the user's previous action
        current_status = tunnel_data.get('status', 'OFF')
        user_previous_status = tunnel_data.get(user_id, 0)

        if current_status == 'OFF' or user_previous_status == 0:
            # Update status to ON
            new_status = 'ON'
            train_cnt = tunnel_data.get('train_cnt', 0) + 1
            user_status = 1
        else:
            # User is already ON, can't turn ON again
            return {'message': 'User has already turned ON the train status.'}

    else:
        # Get the current tunnel data
        tunnel_ref = firebase_admin.db.reference(f'/{tunnel_id}')
        tunnel_data = tunnel_ref.get()

        # Check the current status and the user's previous action
        current_status = tunnel_data.get('status', 'ON')
        user_previous_status = tunnel_data.get(user_id, 1)
        train_cnt = tunnel_data.get('train_cnt', 0)

        if current_status == 'ON' and user_previous_status == 1:
            if train_cnt == 1:
                # Last user turning OFF the train status, set status to OFF
                new_status = 'OFF'
                train_cnt = 0
                user_status = 0
            elif train_cnt > 1:
                # Decrease train count but keep status ON
                new_status = 'ON'
                train_cnt -= 1
                user_status = 0
            else:
                return {'message': 'Error: Train count is invalid.'}
        else:
            # User is already OFF, can't turn OFF again
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
    radius=data.get('radius')

    try:
        result = update_train_status(user_id, tunnel_id, distance,radius)
        return jsonify(result), 200
    except Exception as e:
        print(f"Error updating train status: {e}")
        return jsonify({'message': 'Internal Server Error'}), 500


#logout




if __name__ == "__main__":
    app.run()
