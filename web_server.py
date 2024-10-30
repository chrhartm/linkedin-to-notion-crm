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
from notion_client.errors import APIResponseError
import traceback

app = Flask(__name__, static_folder='static')
CORS(app)  # Enable CORS for all routes
app.secret_key = os.urandom(24)
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}
SYNC_TIMEOUT = 300  # 5 minutes timeout
MAX_RETRIES = 3  # Maximum number of retries for failed operations

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Global variable to track sync progress
sync_progress = {
    'total': 0,
    'current': 0,
    'status': 'idle',
    'last_update': time(),
    'error': None,
    'retry_count': 0
}

class SyncError:
    FILE_UPLOAD = "FILE_UPLOAD_ERROR"
    NOTION_API = "NOTION_API_ERROR"
    FILE_PROCESSING = "FILE_PROCESSING_ERROR"
    NETWORK = "NETWORK_ERROR"
    TIMEOUT = "TIMEOUT_ERROR"
    VALIDATION = "VALIDATION_ERROR"
    RETRY_FAILED = "RETRY_FAILED"

def error_response(error_type, message, details=None, status_code=400):
    error_data = {
        'status': 'error',
        'error_type': error_type,
        'message': message,
    }
    if details:
        error_data['details'] = details
    logging.error(f"Error response: {error_type} - {message} - {details}")
    return jsonify(error_data), status_code

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def error_handler(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except APIResponseError as e:
            logging.error(f"Notion API Error in {f.__name__}: {str(e)}\n{traceback.format_exc()}")
            return error_response(
                error_type=SyncError.NOTION_API,
                message="Error connecting to Notion API",
                details=str(e),
                status_code=400
            )
        except Exception as e:
            logging.error(f"Unexpected error in {f.__name__}: {str(e)}\n{traceback.format_exc()}")
            return error_response(
                error_type=SyncError.NETWORK,
                message="An unexpected error occurred",
                details=str(e),
                status_code=500
            )
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
        'error': None,
        'retry_count': 0
    }

    # Validate file upload
    if 'linkedin_file' not in request.files:
        return error_response(
            error_type=SyncError.VALIDATION,
            message='No file uploaded',
            details='Please select a LinkedIn connections export file'
        )
    
    file = request.files['linkedin_file']
    if file.filename == '':
        return error_response(
            error_type=SyncError.VALIDATION,
            message='No file selected',
            details='Please choose a file before uploading'
        )
    
    if not allowed_file(file.filename):
        return error_response(
            error_type=SyncError.VALIDATION,
            message='Invalid file type',
            details='Please upload a CSV file exported from LinkedIn'
        )

    try:
        # Save the uploaded file
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        # Validate Notion credentials
        notion_token = request.form.get('notion_token')
        notion_database_id = request.form.get('notion_database_id')
        
        if not notion_token or not notion_database_id:
            return error_response(
                error_type=SyncError.VALIDATION,
                message='Missing Notion credentials',
                details='Both Notion token and database ID are required'
            )

        os.environ['NOTION_TOKEN'] = notion_token
        os.environ['NOTION_DATABASE_ID'] = notion_database_id

        try:
            notion_manager = NotionManager()
            linkedin_parser = LinkedInParser()
            contact_manager = ContactManager(notion_manager, linkedin_parser)

            # Parse contacts first to get total count
            try:
                contacts = linkedin_parser.parse_linkedin_export(filepath)
                if not contacts:
                    return error_response(
                        error_type=SyncError.FILE_PROCESSING,
                        message='No contacts found in the file',
                        details='The LinkedIn export file appears to be empty'
                    )
            except Exception as e:
                logging.error(f"File processing error: {str(e)}\n{traceback.format_exc()}")
                return error_response(
                    error_type=SyncError.FILE_PROCESSING,
                    message='Error processing LinkedIn export file',
                    details=str(e)
                )

            sync_progress['total'] = len(contacts)
            sync_progress['status'] = 'syncing'

            # Sync contacts with progress tracking and retry logic
            for i, contact in enumerate(contacts):
                retry_count = 0
                while retry_count < MAX_RETRIES:
                    try:
                        notion_manager.add_contact(contact)
                        sync_progress['current'] = i + 1
                        sync_progress['last_update'] = time()
                        break
                    except APIResponseError as e:
                        retry_count += 1
                        if retry_count >= MAX_RETRIES:
                            sync_progress['error'] = {
                                'error_type': SyncError.NOTION_API,
                                'message': f"Error syncing contact {contact.get('Name', 'Unknown')} after {MAX_RETRIES} retries",
                                'details': str(e)
                            }
                            logging.error(f"Failed to sync contact after {MAX_RETRIES} retries: {str(e)}")
                        else:
                            logging.warning(f"Retry {retry_count} for contact {contact.get('Name', 'Unknown')}")
                    except Exception as e:
                        retry_count += 1
                        if retry_count >= MAX_RETRIES:
                            sync_progress['error'] = {
                                'error_type': SyncError.NETWORK,
                                'message': f"Error syncing contact {contact.get('Name', 'Unknown')} after {MAX_RETRIES} retries",
                                'details': str(e)
                            }
                            logging.error(f"Failed to sync contact after {MAX_RETRIES} retries: {str(e)}")
                        else:
                            logging.warning(f"Retry {retry_count} for contact {contact.get('Name', 'Unknown')}")

            if not sync_progress['error']:
                sync_progress['status'] = 'completed'

        except APIResponseError as e:
            logging.error(f"Notion API Error: {str(e)}\n{traceback.format_exc()}")
            return error_response(
                error_type=SyncError.NOTION_API,
                message='Error connecting to Notion API',
                details=str(e)
            )
        except Exception as e:
            logging.error(f"Unexpected error: {str(e)}\n{traceback.format_exc()}")
            return error_response(
                error_type=SyncError.NETWORK,
                message='Unexpected error during sync process',
                details=str(e)
            )
        finally:
            # Clean up uploaded file
            if os.path.exists(filepath):
                os.remove(filepath)

        return jsonify({
            'status': 'success',
            'message': 'Sync process started successfully'
        })

    except Exception as e:
        logging.error(f"Error in sync process: {str(e)}\n{traceback.format_exc()}")
        sync_progress['status'] = 'error'
        sync_progress['error'] = {
            'error_type': SyncError.NETWORK,
            'message': 'Unexpected error during sync process',
            'details': str(e)
        }
        return error_response(
            error_type=SyncError.NETWORK,
            message='Unexpected error during sync process',
            details=str(e)
        )

@app.route('/sync/progress')
@error_handler
def get_sync_progress():
    global sync_progress
    
    try:
        # Check for timeout
        if sync_progress['status'] in ['starting', 'syncing']:
            if time() - sync_progress['last_update'] > SYNC_TIMEOUT:
                sync_progress['status'] = 'error'
                sync_progress['error'] = {
                    'error_type': SyncError.TIMEOUT,
                    'message': 'Sync operation timed out',
                    'details': 'The operation took longer than the maximum allowed time'
                }
                logging.error("Sync operation timed out")
        
        response = {
            'status': sync_progress['status'],
            'total': sync_progress['total'],
            'current': sync_progress['current'],
        }
        
        if sync_progress['error']:
            response.update(sync_progress['error'])
        
        return jsonify(response)
        
    except Exception as e:
        logging.error(f"Error fetching progress: {str(e)}\n{traceback.format_exc()}")
        return error_response(
            error_type=SyncError.NETWORK,
            message='Error fetching sync progress',
            details=str(e)
        )

@app.route('/api/contacts')
@error_handler
def get_contacts():
    try:
        notion_manager = NotionManager()
        contacts = notion_manager.get_all_contacts()
        return jsonify({
            "status": "success",
            "contacts": contacts
        })
    except APIResponseError as e:
        return error_response(
            error_type=SyncError.NOTION_API,
            message='Error retrieving contacts from Notion',
            details=str(e)
        )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)
