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
            "Contact Schedule": {"select": {
                "options": [
                    {"name": "Never", "color": "gray"},
                    {"name": "Weekly", "color": "blue"},
                    {"name": "Monthly", "color": "green"},
                    {"name": "Quarterly", "color": "yellow"},
                    {"name": "Yearly", "color": "red"}
                ]
            }},
            "Overdue": {"formula": {
                "expression": """
                if(prop("Contact Schedule") == "Never", false,
                if(prop("Contact Schedule") == "Weekly", dateBetween(prop("Last Contacted"), now(), "weeks") > 1,
                if(prop("Contact Schedule") == "Monthly", dateBetween(prop("Last Contacted"), now(), "months") > 1,
                if(prop("Contact Schedule") == "Quarterly", dateBetween(prop("Last Contacted"), now(), "quarters") > 1,
                if(prop("Contact Schedule") == "Yearly", dateBetween(prop("Last Contacted"), now(), "years") > 1,
                false)))))
                """
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

        try:
            self.client.databases.update(
                database_id=self.database_id,
                properties=properties
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
                elif key == "Last Contacted":
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
