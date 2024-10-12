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
        try:
            current_properties = database['properties']
            
            new_properties = {
                "Name": {"title": {}},
                "LinkedIn URL": {"url": {}},
                "Company": {"rich_text": {}},
                "Position": {"rich_text": {}},
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
                "Connected On": {"date": {}},
                "Contact Schedule": {"select": {
                    "options": [
                        {"name": "Never", "color": "gray"},
                        {"name": "Weekly", "color": "blue"},
                        {"name": "Biweekly", "color": "green"},
                        {"name": "Monthly", "color": "yellow"},
                        {"name": "Quarterly", "color": "orange"},
                        {"name": "Biannually", "color": "red"},
                        {"name": "Yearly", "color": "purple"}
                    ]
                }},
                'Overdue': {'formula': {
                    'expression': 'now() > dateAdd(prop("Last Contacted"), 30, "days")'
                }},
                "Email": {"email": {}},
                "Tags": {"multi_select": {
                    "options": [
                        {"name": "Important", "color": "red"},
                        {"name": "Follow-up", "color": "blue"},
                        {"name": "New Connection", "color": "green"}
                    ]
                }},
            }

            # Merge existing properties with new properties
            for prop_name, prop_value in new_properties.items():
                if prop_name not in current_properties:
                    current_properties[prop_name] = prop_value
                elif prop_value.get('select') or prop_value.get('multi_select'):
                    # For select and multi_select, merge options
                    existing_options = set(option['name'] for option in current_properties[prop_name].get('select', {}).get('options', []))
                    for new_option in prop_value.get('select', {}).get('options', []):
                        if new_option['name'] not in existing_options:
                            current_properties[prop_name]['select']['options'].append(new_option)

            self.client.databases.update(
                database_id=self.database_id,
                properties=current_properties
            )
            logging.info(f"Updated database properties for database ID: {self.database_id}")
        except Exception as e:
            logging.error(f"Error updating database properties: {str(e)}")
            raise ValueError(f"Failed to update database properties. Error: {str(e)}")

    def print_database_properties(self):
        try:
            database = self.client.databases.retrieve(database_id=self.database_id)
            properties = database.get('properties', {})
            print("Database Properties:")
            for key, value in properties.items():
                print(f"- {key}: {value['type']}")
        except Exception as e:
            logging.error(f"Error retrieving database properties: {str(e)}")
            print(f"Error retrieving database properties: {str(e)}")

    def add_contact(self, contact):
        try:
            properties = {
                "Name": {"title": [{"text": {"content": contact["Name"]}}]},
                "LinkedIn URL": {"url": contact["LinkedIn URL"]},
                "Company": {"rich_text": [{"text": {"content": contact["Company"]}}]},
                "Position": {"rich_text": [{"text": {"content": contact["Position"]}}]},
                "Industry": {"select": {"name": contact["Industry"]}},
                "Field of Work": {"select": {"name": contact["Field of Work"]}},
                "Last Contacted": {"date": {"start": contact["Last Contacted"]}},
                "Connected On": {"date": {"start": contact["Connected On"]}},
                "Contact Schedule": {"select": {"name": contact["Contact Schedule"]}},
            }
            self.client.pages.create(parent={"database_id": self.database_id}, properties=properties)
            logging.info(f"Added contact: {contact['Name']}")
        except Exception as e:
            logging.error(f"Error adding contact: {str(e)}")
            raise

    def update_contact(self, page_id, updates):
        try:
            properties = {}
            for key, value in updates.items():
                if key == "Name":
                    properties[key] = {"title": [{"text": {"content": value}}]}
                elif key == "LinkedIn URL":
                    properties[key] = {"url": value}
                elif key in ["Company", "Position"]:
                    properties[key] = {"rich_text": [{"text": {"content": value}}]}
                elif key in ["Industry", "Field of Work", "Contact Schedule"]:
                    properties[key] = {"select": {"name": value}}
                elif key in ["Last Contacted", "Connected On"]:
                    properties[key] = {"date": {"start": value}}
            
            self.client.pages.update(page_id=page_id, properties=properties)
            logging.info(f"Updated contact with page ID: {page_id}")
        except Exception as e:
            logging.error(f"Error updating contact: {str(e)}")
            raise

    def get_all_contacts(self):
        try:
            results = self.client.databases.query(database_id=self.database_id)
            contacts = results.get("results", [])
            logging.info(f"Retrieved {len(contacts)} contacts from the database")
            return contacts
        except Exception as e:
            logging.error(f"Error retrieving contacts: {str(e)}")
            raise