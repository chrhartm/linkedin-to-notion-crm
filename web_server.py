# Monkey patch at the very beginning before other imports
import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, jsonify, request, flash, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit, disconnect
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
import ssl
import re

app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = os.urandom(24)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Function to validate Replit domains
def is_valid_replit_domain(origin):
    if not origin:
        return False
    replit_patterns = [
        r'^https?://.*\.repl\.co$',
        r'^https?://.*\.replit\.dev$',
        r'^https?://.*\.repl\.it$'
    ]
    return any(re.match(pattern, origin) for pattern in replit_patterns)

# Update CORS configuration for production
CORS(app, resources={
    r"/*": {
        "origins": "*",  # Will be filtered by Socket.IO
        "methods": ["GET", "POST"],
        "allow_headers": ["Content-Type"],
        "supports_credentials": True
    }
})

# Configure SocketIO with enhanced production settings
socketio = SocketIO(
    app,
    cors_allowed_origins="*",  # Will be filtered by our custom validation
    async_mode='eventlet',
    ping_timeout=60,
    ping_interval=25,
    manage_session=False,
    logger=True,
    engineio_logger=True,
    transports=['websocket', 'polling'],
    always_connect=True,
    reconnection=True,
    reconnection_attempts=10,
    reconnection_delay=1000,
    reconnection_delay_max=5000,
    randomization_factor=0.5,
    cookie=None,
    max_http_buffer_size=1024 * 1024,  # 1MB
    http_compression=True,
    ssl_verify=False if os.environ.get('REPL_SLUG') else True  # Disable SSL verification on Replit
)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}
SYNC_TIMEOUT = 600  # 10 minutes timeout
MAX_RETRIES = 3
MAX_QUEUE_SIZE = 10

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Global variables for sync state management
sync_queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)
sync_lock = threading.Lock()
active_connections = set()
connection_timestamps = {}

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
    logging.error(f"Error response: {error_type} - {message} - {details}")
    return jsonify(error_data), status_code

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def emit_sync_progress(data, room=None):
    with app.app_context():
        try:
            if room in active_connections:  # Only emit if connection is still active
                socketio.emit('sync_progress', data, room=room)
        except Exception as e:
            logging.error(f"Error emitting sync progress: {str(e)}")

def process_sync_queue():
    while True:
        try:
            sync_data = sync_queue.get()
            if sync_data is None:  # Shutdown signal
                break

            room = sync_data.get('room')
            if room not in active_connections:  # Skip if client disconnected
                continue

            emit_sync_progress({
                'status': 'processing',
                'message': 'Starting sync process...'
            }, room)

            filepath = sync_data['filepath']
            notion_token = sync_data['notion_token']
            notion_database_id = sync_data['notion_database_id']

            try:
                os.environ['NOTION_TOKEN'] = notion_token
                os.environ['NOTION_DATABASE_ID'] = notion_database_id

                notion_manager = NotionManager()
                linkedin_parser = LinkedInParser()
                contact_manager = ContactManager(notion_manager, linkedin_parser)

                # Parse LinkedIn contacts
                emit_sync_progress({
                    'status': 'processing',
                    'message': 'Parsing LinkedIn export file...'
                }, room)
                
                linkedin_contacts = linkedin_parser.parse_linkedin_export(filepath)
                total_contacts = len(linkedin_contacts)
                
                # Get existing contacts
                emit_sync_progress({
                    'status': 'processing',
                    'message': 'Fetching existing contacts...'
                }, room)
                
                existing_contacts = notion_manager.get_all_contacts()
                existing_urls = {
                    contact['properties'].get('LinkedIn URL', {}).get('url'): contact['id']
                    for contact in existing_contacts
                    if contact['properties'].get('LinkedIn URL', {}).get('url')
                }
                
                emit_sync_progress({
                    'status': 'processing',
                    'total': total_contacts,
                    'current': 0,
                    'message': f'Found {total_contacts} contacts to process'
                }, room)

                for i, contact in enumerate(linkedin_contacts, 1):
                    if room not in active_connections:  # Stop if client disconnected
                        break

                    retry_count = 0
                    while retry_count < MAX_RETRIES:
                        try:
                            linkedin_url = contact.get('LinkedIn URL')
                            action = 'Updating' if linkedin_url in existing_urls else 'Adding'
                            
                            if linkedin_url in existing_urls:
                                notion_manager.update_contact(existing_urls[linkedin_url], contact)
                            else:
                                notion_manager.add_contact(contact)
                            
                            emit_sync_progress({
                                'status': 'processing',
                                'total': total_contacts,
                                'current': i,
                                'message': f'{action} contact: {contact.get("Name", "Unknown")} ({i}/{total_contacts})',
                                'contact': contact.get('Name', 'Unknown')
                            }, room)
                            break
                        except Exception as e:
                            retry_count += 1
                            if retry_count >= MAX_RETRIES:
                                raise e
                            emit_sync_progress({
                                'status': 'retrying',
                                'message': f'Retry {retry_count}/{MAX_RETRIES} for contact {contact.get("Name", "Unknown")}'
                            }, room)

                if room in active_connections:  # Only emit completion if client still connected
                    emit_sync_progress({
                        'status': 'completed',
                        'total': total_contacts,
                        'current': total_contacts,
                        'message': 'Sync completed successfully!'
                    }, room)

            except Exception as e:
                if room in active_connections:  # Only emit error if client still connected
                    error_type = (
                        SyncError.NOTION_API if isinstance(e, APIResponseError)
                        else SyncError.NETWORK
                    )
                    emit_sync_progress({
                        'status': 'error',
                        'error_type': error_type,
                        'message': str(e),
                        'details': traceback.format_exc()
                    }, room)
            finally:
                # Clean up the uploaded file
                if os.path.exists(filepath):
                    os.remove(filepath)
                sync_queue.task_done()

        except Exception as e:
            logging.error(f"Queue processing error: {str(e)}\n{traceback.format_exc()}")

# Start the queue processing thread
sync_thread = threading.Thread(target=process_sync_queue, daemon=True)
sync_thread.start()

def check_connection_health():
    """Monitor connection health and clean up stale connections"""
    current_time = time()
    stale_connections = set()
    
    for sid in active_connections:
        if current_time - connection_timestamps.get(sid, 0) > 120:  # 2 minutes timeout
            stale_connections.add(sid)
    
    for sid in stale_connections:
        active_connections.discard(sid)
        connection_timestamps.pop(sid, None)
        logging.warning(f"Removed stale connection: {sid}")

@socketio.on('connect')
def handle_connect():
    origin = request.headers.get('Origin', '')
    if not is_valid_replit_domain(origin):
        logging.warning(f"Rejected connection from unauthorized origin: {origin}")
        disconnect()
        return False
    
    active_connections.add(request.sid)
    connection_timestamps[request.sid] = time()
    logging.info(f"Client connected: {request.sid}")
    return True

@socketio.on('disconnect')
def handle_disconnect():
    active_connections.discard(request.sid)
    connection_timestamps.pop(request.sid, None)
    logging.info(f"Client disconnected: {request.sid}")

@socketio.on('ping')
def handle_ping():
    """Handle client ping to keep connection alive"""
    if request.sid in active_connections:
        connection_timestamps[request.sid] = time()
        return {'status': 'ok'}

@socketio.on_error_default
def default_error_handler(e):
    logging.error(f"SocketIO error: {str(e)}\n{traceback.format_exc()}")
    return {"error": str(e)}

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
        # Check connection health before processing new request
        check_connection_health()
        
        # Check if queue is full
        if sync_queue.full():
            return error_response(
                error_type=SyncError.QUEUE_FULL,
                message="Sync queue is full",
                details="Please try again later when current operations complete"
            )

        # Get socket_id from form data
        socket_id = request.form.get('socket_id')
        if not socket_id or socket_id not in active_connections:
            return error_response(
                error_type=SyncError.VALIDATION,
                message="Invalid or missing socket ID",
                details="Socket connection not established or expired"
            )

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

        # Add to processing queue with socket room ID
        sync_queue.put({
            'filepath': filepath,
            'notion_token': notion_token,
            'notion_database_id': notion_database_id,
            'room': socket_id
        })

        return jsonify({
            'status': 'success',
            'message': 'Sync process started'
        })

    except Exception as e:
        logging.error(f"Error in sync process: {str(e)}\n{traceback.format_exc()}")
        return error_response(
            error_type=SyncError.NETWORK,
            message='Unexpected error during sync process',
            details=str(e)
        )

if __name__ == '__main__':
    socketio.run(
        app,
        host='0.0.0.0',
        port=3000,
        debug=False,  # Disable debug mode in production
        allow_unsafe_werkzeug=True,  # Required for eventlet
        log_output=True
    )
