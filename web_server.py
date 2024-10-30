from flask import Flask, render_template, jsonify
from notion_manager import NotionManager
import os
import logging

app = Flask(__name__)
notion_manager = NotionManager()

@app.route('/')
def home():
    try:
        contacts = notion_manager.get_all_contacts()
        return jsonify({
            "status": "success",
            "contacts": len(contacts),
            "message": "Personal CRM API is running"
        })
    except Exception as e:
        logging.error(f"Error in home route: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/contacts')
def get_contacts():
    try:
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
    app.run(host='0.0.0.0', port=3000)
