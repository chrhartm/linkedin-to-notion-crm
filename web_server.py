from flask import Flask, render_template, jsonify, request, flash, send_from_directory
from werkzeug.utils import secure_filename
from notion_manager import NotionManager
from linkedin_parser import LinkedInParser
from contact_manager import ContactManager
import os
import logging

app = Flask(__name__, static_folder='static')
app.secret_key = os.urandom(24)
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Global variable to track sync progress
sync_progress = {
    'total': 0,
    'current': 0,
    'status': 'idle'
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
        global sync_progress
        sync_progress = {'total': 0, 'current': 0, 'status': 'starting'}

        if 'linkedin_file' not in request.files:
            return render_template('index.html', message='No file uploaded', error=True)
        
        file = request.files['linkedin_file']
        if file.filename == '':
            return render_template('index.html', message='No file selected', error=True)
        
        if not allowed_file(file.filename):
            return render_template('index.html', message='Invalid file type. Please upload a CSV file.', error=True)

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
            notion_manager.add_contact(contact)
            sync_progress['current'] = i + 1

        sync_progress['status'] = 'completed'

        # Clean up uploaded file
        os.remove(filepath)

        return jsonify({'status': 'success', 'message': 'Sync started successfully'})
    except Exception as e:
        logging.error(f"Error syncing contacts: {str(e)}")
        sync_progress['status'] = 'error'
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/sync/progress')
def get_sync_progress():
    return jsonify(sync_progress)

@app.route('/api/contacts')
def get_contacts():
    try:
        notion_manager = NotionManager()
        contacts = notion_manager.get_all_contacts()
        return jsonify({
            "status": "success",
            "contacts": contacts
        })
    except Exception as e:
        logging.error(f"Error fetching contacts: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)
