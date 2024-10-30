from flask import Flask, render_template, jsonify, request, flash, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from notion_manager import NotionManager
from linkedin_parser import LinkedInParser
from contact_manager import ContactManager
import os
import logging
from functools import wraps
from time import time

app = Flask(__name__, static_folder='static')
CORS(app)  # Enable CORS for all routes
app.secret_key = os.urandom(24)
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}
SYNC_TIMEOUT = 300  # 5 minutes timeout

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Global variable to track sync progress
sync_progress = {
    'total': 0,
    'current': 0,
    'status': 'idle',
    'last_update': time(),
    'error': None
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def error_handler(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logging.error(f"Error in {f.__name__}: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': f"An error occurred: {str(e)}"
            }), 500
    return decorated_function

@app.route('/')
@error_handler
def home():
    return render_template('index.html')

@app.route('/howto-linkedin.png')
@error_handler
def serve_linkedin_image():
    return send_from_directory('assets', 'howto-linkedin.png')

@app.route('/howto-notion.png')
@error_handler
def serve_notion_image():
    return send_from_directory('assets', 'howto-notion.png')

@app.route('/sync', methods=['POST'])
@error_handler
def sync_contacts():
    global sync_progress
    sync_progress = {
        'total': 0,
        'current': 0,
        'status': 'starting',
        'last_update': time(),
        'error': None
    }

    if 'linkedin_file' not in request.files:
        return jsonify({
            'status': 'error',
            'message': 'No file uploaded'
        }), 400
    
    file = request.files['linkedin_file']
    if file.filename == '':
        return jsonify({
            'status': 'error',
            'message': 'No file selected'
        }), 400
    
    if not allowed_file(file.filename):
        return jsonify({
            'status': 'error',
            'message': 'Invalid file type. Please upload a CSV file.'
        }), 400

    try:
        # Save the uploaded file
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        # Initialize managers with provided tokens
        notion_token = request.form.get('notion_token')
        notion_database_id = request.form.get('notion_database_id')
        os.environ['NOTION_TOKEN'] = notion_token
        os.environ['NOTION_DATABASE_ID'] = notion_database_id

        notion_manager = NotionManager()
        linkedin_parser = LinkedInParser()
        contact_manager = ContactManager(notion_manager, linkedin_parser)

        # Parse contacts first to get total count
        contacts = linkedin_parser.parse_linkedin_export(filepath)
        sync_progress['total'] = len(contacts)
        sync_progress['status'] = 'syncing'

        # Sync contacts with progress tracking
        for i, contact in enumerate(contacts):
            try:
                notion_manager.add_contact(contact)
                sync_progress['current'] = i + 1
                sync_progress['last_update'] = time()
            except Exception as e:
                sync_progress['error'] = f"Error syncing contact {contact.get('Name', 'Unknown')}: {str(e)}"
                logging.error(sync_progress['error'])

        sync_progress['status'] = 'completed'

        # Clean up uploaded file
        os.remove(filepath)

        return jsonify({
            'status': 'success',
            'message': 'Sync started successfully'
        })

    except Exception as e:
        logging.error(f"Error syncing contacts: {str(e)}")
        sync_progress['status'] = 'error'
        sync_progress['error'] = str(e)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/sync/progress')
@error_handler
def get_sync_progress():
    # Check for timeout
    if sync_progress['status'] in ['starting', 'syncing']:
        if time() - sync_progress['last_update'] > SYNC_TIMEOUT:
            sync_progress['status'] = 'error'
            sync_progress['error'] = 'Sync operation timed out'
            
    return jsonify({
        'status': sync_progress['status'],
        'total': sync_progress['total'],
        'current': sync_progress['current'],
        'error': sync_progress['error']
    })

@app.route('/api/contacts')
@error_handler
def get_contacts():
    notion_manager = NotionManager()
    contacts = notion_manager.get_all_contacts()
    return jsonify({
        "status": "success",
        "contacts": contacts
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)
