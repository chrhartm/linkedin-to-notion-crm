# Monkey patch at the very beginning before other imports
import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, jsonify, request, flash, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
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
import queue
import threading

app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = os.urandom(24)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}
SYNC_TIMEOUT = 600  # 10 minutes timeout
MAX_RETRIES = 3
MAX_QUEUE_SIZE = 10

# Configure logging with more detailed format and DEBUG level
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Global variables for sync state management
sync_queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)
sync_lock = threading.Lock()

class SyncError:
    FILE_UPLOAD = "FILE_UPLOAD_ERROR"
    NOTION_API = "NOTION_API_ERROR"
    FILE_PROCESSING = "FILE_PROCESSING_ERROR"
    NETWORK = "NETWORK_ERROR"
    TIMEOUT = "TIMEOUT_ERROR"
    VALIDATION = "VALIDATION_ERROR"
    RETRY_FAILED = "RETRY_FAILED"
    QUEUE_FULL = "QUEUE_FULL_ERROR"

def error_response(error_type, message, details=None, status_code=400):
    error_data = {
        'status': 'error',
        'error_type': error_type,
        'message': message,
    }
    if details:
        error_data['details'] = details
    logging.error(f"Error response: [{error_type}] - Message: {message} - Details: {details}")
    return jsonify(error_data), status_code

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def emit_sync_progress(data, room=None):
    with app.app_context():
        try:
            socketio.emit('sync_progress', data, room=room)
            logging.debug(f"Progress emitted: {data.get('status')} - {data.get('message')}")
        except Exception as e:
            logging.error(f"Error emitting sync progress: {str(e)}")

def process_sync_queue():
    while True:
        try:
            sync_data = sync_queue.get()
            if sync_data is None:  # Shutdown signal
                logging.info("Received shutdown signal, stopping sync queue processor")
                break

            room = sync_data.get('room')
            logging.info(f"Starting sync process for session: {room}")
            emit_sync_progress({
                'status': 'processing',
                'message': 'Starting sync process...'
            }, room)

            filepath = sync_data['filepath']
            notion_token = sync_data['notion_token']
            notion_database_id = sync_data['notion_database_id']

            try:
                start_time = time()
                os.environ['NOTION_TOKEN'] = notion_token
                os.environ['NOTION_DATABASE_ID'] = notion_database_id

                # Initialize managers and create ContactManager instance
                logging.info("Initializing NotionManager and LinkedInParser")
                notion_manager = NotionManager()
                linkedin_parser = LinkedInParser()
                contact_manager = ContactManager(notion_manager, linkedin_parser)

                # Step 1: Parse LinkedIn contacts
                logging.info(f"Starting LinkedIn file parsing: {filepath}")
                emit_sync_progress({
                    'status': 'processing',
                    'message': 'Loading LinkedIn contacts from CSV file...'
                }, room)
                linkedin_contacts = linkedin_parser.parse_linkedin_export(filepath)
                logging.info(f"Successfully parsed {len(linkedin_contacts)} contacts from LinkedIn CSV")

                # Step 2: Load Notion contacts
                emit_sync_progress({
                    'status': 'processing',
                    'message': 'Loading existing contacts from Notion database...'
                }, room)
                existing_contacts = contact_manager.get_all_contacts()
                logging.info(f"Retrieved {len(existing_contacts)} existing contacts from Notion database")

                total_contacts = len(linkedin_contacts)
                valid_contacts = sum(1 for c in linkedin_contacts if contact_manager._is_valid_contact(c))
                logging.info(f"Found {valid_contacts} valid contacts out of {total_contacts} total contacts")

                emit_sync_progress({
                    'status': 'processing',
                    'message': f'Processing {valid_contacts} valid LinkedIn contacts...',
                    'total': valid_contacts,
                    'current': 0
                }, room)

                # Step 3: Sync contacts
                processed_count = 0
                skipped_count = 0
                updated_count = 0
                added_count = 0
                for index, contact in enumerate(linkedin_contacts, 1):
                    contact_name = contact.get('Name', 'Unknown Contact')
                    
                    if not contact_manager._is_valid_contact(contact):
                        skipped_count += 1
                        logging.debug(f"Skipping invalid contact: {contact_name}")
                        continue

                    processed_count += 1
                    logging.info(f"Processing contact {processed_count}/{valid_contacts}: {contact_name}")
                    
                    emit_sync_progress({
                        'status': 'processing',
                        'message': f'Processing contact {processed_count} of {valid_contacts}',
                        'contact': contact_name,
                        'total': valid_contacts,
                        'current': processed_count
                    }, room)

                    # Process the contact using ContactManager
                    try:
                        existing_contact = next(
                            (existing for existing in existing_contacts 
                             if existing['properties'].get('LinkedIn URL', {}).get('url') == contact.get('LinkedIn URL')),
                            None
                        )
                        
                        if existing_contact:
                            # Check if contact actually needed updates
                            if contact_manager._has_changes(existing_contact, contact):
                                contact_manager._process_single_contact(contact, existing_contacts)
                                updated_count += 1
                                logging.info(f"Updated contact with changes: {contact.get('Name')}")
                            else:
                                skipped_count += 1
                                logging.info(f"Skipped contact (no changes): {contact.get('Name')}")
                        else:
                            contact_manager._process_single_contact(contact, existing_contacts)
                            added_count += 1
                            logging.info(f"Added new contact: {contact.get('Name')}")
                    except Exception as e:
                        logging.error(f"Error processing contact {contact_name}: {str(e)}")
                        raise

                end_time = time()
                duration = round(end_time - start_time, 2)
                success_message = (
                    f"Sync completed successfully in {duration}s! "
                    f"Processed {processed_count} contacts "
                    f"({added_count} added, {updated_count} updated, {skipped_count} skipped)"
                )
                logging.info(success_message)
                
                emit_sync_progress({
                    'status': 'completed',
                    'message': success_message
                }, room)

            except APIResponseError as e:
                logging.error(f"Notion API Error: {str(e)}\n{traceback.format_exc()}")
                emit_sync_progress({
                    'status': 'error',
                    'error_type': SyncError.NOTION_API,
                    'message': str(e),
                    'details': traceback.format_exc()
                }, room)
            except Exception as e:
                error_type = SyncError.NETWORK if "connection" in str(e).lower() else SyncError.FILE_PROCESSING
                logging.error(f"{error_type} Error: {str(e)}\n{traceback.format_exc()}")
                emit_sync_progress({
                    'status': 'error',
                    'error_type': error_type,
                    'message': str(e),
                    'details': traceback.format_exc()
                }, room)
            finally:
                # Clean up the uploaded file
                if os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                        logging.info(f"Cleaned up temporary file: {filepath}")
                    except Exception as e:
                        logging.warning(f"Error cleaning up file {filepath}: {str(e)}")
                sync_queue.task_done()

        except Exception as e:
            logging.error(f"Queue processing error: {str(e)}\n{traceback.format_exc()}")

# Start the queue processing thread
sync_thread = threading.Thread(target=process_sync_queue, daemon=True)
sync_thread.start()

@socketio.on('connect')
def handle_connect():
    logging.info(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    logging.info(f"Client disconnected: {request.sid}")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/howto-linkedin.png')
def serve_linkedin_image():
    return send_from_directory('assets', 'howto-linkedin.png')

@app.route('/howto-notion.png')
def serve_notion_image():
    return send_from_directory('assets', 'howto-notion.png')

@app.route('/sync', methods=['POST'])
def sync_contacts():
    try:
        # Check if queue is full
        if sync_queue.full():
            logging.warning("Sync queue is full, rejecting new request")
            return error_response(
                error_type=SyncError.QUEUE_FULL,
                message="Sync queue is full",
                details="Please try again later when current operations complete"
            )

        # Get socket_id from form data
        socket_id = request.form.get('socket_id')
        if not socket_id:
            logging.error("Missing socket ID in request")
            return error_response(
                error_type=SyncError.VALIDATION,
                message="Missing socket ID",
                details="Socket connection not established"
            )

        # Validate file upload
        if 'linkedin_file' not in request.files:
            logging.error("No file part in request")
            return error_response(
                error_type=SyncError.VALIDATION,
                message='No file uploaded',
                details='Please select a LinkedIn connections export file'
            )
        
        file = request.files['linkedin_file']
        if file.filename == '':
            logging.error("No selected file in request")
            return error_response(
                error_type=SyncError.VALIDATION,
                message='No file selected',
                details='Please choose a file before uploading'
            )
        
        if not allowed_file(file.filename):
            logging.error(f"Invalid file type: {file.filename}")
            return error_response(
                error_type=SyncError.VALIDATION,
                message='Invalid file type',
                details='Please upload a CSV file exported from LinkedIn'
            )

        # Save the uploaded file
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        logging.info(f"File saved successfully: {filepath}")

        # Validate Notion credentials
        notion_token = request.form.get('notion_token')
        notion_database_id = request.form.get('notion_database_id')
        
        if not notion_token or not notion_database_id:
            logging.error("Missing Notion credentials")
            return error_response(
                error_type=SyncError.VALIDATION,
                message='Missing Notion credentials',
                details='Both Notion token and database ID are required'
            )

        # Add to processing queue with socket room ID
        sync_queue.put({
            'filepath': filepath,
            'notion_token': notion_token,
            'notion_database_id': notion_database_id,
            'room': socket_id
        })
        logging.info(f"Added sync task to queue for session: {socket_id}")

        return jsonify({
            'status': 'success',
            'message': 'Sync process started'
        })

    except Exception as e:
        logging.error(f"Unexpected error in sync process: {str(e)}\n{traceback.format_exc()}")
        return error_response(
            error_type=SyncError.NETWORK,
            message='Unexpected error during sync process',
            details=str(e)
        )

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=3000, debug=True)
