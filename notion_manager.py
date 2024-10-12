from notion_client import Client
from datetime import datetime, timedelta
import logging
import os

class NotionManager:
    def __init__(self):
        self.client = Client(auth=os.getenv("NOTION_TOKEN"))
        self.database_id = os.getenv("NOTION_DATABASE_ID")
        self.ensure_database_exists()

    def ensure_database_exists(self):
        try:
            database = self.client.databases.retrieve(database_id=self.database_id)
            logging.info(f"Connected to existing database with ID: {self.database_id}")
            self.update_database_properties(database)
        except Exception as e:
            logging.error(f"Error connecting to database: {str(e)}")
            raise ValueError(f"Failed to connect to database. Error: {str(e)}")

    def update_database_properties(self, database):
        properties = {
            "Name": {"title": {}},
            "LinkedIn URL": {"url": {}},
            "Company": {"rich_text": {}},
            "Position": {"rich_text": {}},  # Moved 'Position' right after 'Company'
            "Industry": {"select": {
                "options": [
                    {"name": "Technology", "color": "blue"},
                    {"name": "Marketing", "color": "green"},
                    {"name": "Finance", "color": "yellow"},
                    {"name": "Other", "color": "gray"}
                ]
            }},
            "Field of Work": {"select": {
                "options": [
                    {"name": "Software Development", "color": "blue"},
                    {"name": "Data Science", "color": "green"},
                    {"name": "Product Management", "color": "yellow"},
                    {"name": "Other", "color": "gray"}
                ]
            }},
            "Last Contacted": {"date": {}},
            "Contact Schedule": {"select": {
                "options": [
                    {"name": "Weekly", "color": "blue"},
                    {"name": "Monthly", "color": "green"},
                    {"name": "Quarterly", "color": "yellow"},
                    {"name": "Yearly", "color": "red"}
                ]
            }},
            "Overdue": {"checkbox": {}},
            "Email": {"email": {}},
            "Phone": {"phone_number": {}},
            "Tags": {"multi_select": {
                "options": [
                    {"name": "Important", "color": "red"},
                    {"name": "Follow-up", "color": "blue"},
                    {"name": "New Connection", "color": "green"}
                ]
            }},
        }

        try:
            self.client.databases.update(
                database_id=self.database_id,
                properties=properties
            )
            logging.info(f"Updated database properties for database ID: {self.database_id}")
        except Exception as e:
            logging.error(f"Error updating database properties: {str(e)}")
            raise ValueError(f"Failed to update database properties. Error: {str(e)}")

    # Rest of the class implementation remains unchanged
