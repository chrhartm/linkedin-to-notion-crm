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
                "Industry": {"multi_select": {
                    "options": [
                        {"name": "Technology", "color": "blue"},
                        {"name": "Insurance", "color": "green"},
                        {"name": "Banking", "color": "yellow"},
                        {"name": "Healthcare", "color": "red"},
                        {"name": "Manufacturing", "color": "blue"},
                        {"name": "Education", "color": "purple"},
                        {"name": "Retail", "color": "pink"},
                        {"name": "Automotive", "color": "orange"},
                        {"name": "Construction", "color": "brown"},
                        {"name": "Real Estate", "color": "green"},
                        {"name": "Hospitality", "color": "yellow"},
                        {"name": "Energy", "color": "gray"},
                        {"name": "Other", "color": "gray"}
                    ]
                }},
                "Field of Work": {"multi_select": {
                    "options": [
                        {"name": "Software Development", "color": "blue"},
                        {"name": "Marketing", "color": "green"},
                        {"name": "Sales", "color": "red"},
                        {"name": "Operations", "color": "yellow"},
                        {"name": "Other", "color": "gray"}
                    ]
                }},
                "Last Contacted": {"date": {}},
                "Connected On": {"date": {}},
                "Contact Schedule": {"select": {
                    "options": [
                        {"name": "Daily", "color": "red"},
                        {"name": "Weekly", "color": "blue"},
                        {"name": "Monthly", "color": "yellow"},
                        {"name": "Yearly", "color": "brown"},
                        {"name": "As Needed", "color": "gray"}
                    ]
                }},
                "Email": {"email": {}},
                "Connection": {"select": {
                    "options": [
                        {"name": "Minimal", "color": "red"},
                        {"name": "Would answer", "color": "blue"},
                        {"name": "Friend", "color": "green"}
                    ]
                }},
                "Community": {"multi_select": {
                    "options": [
                        {"name": "University", "color": "red"},
                        {"name": "High-School", "color": "blue"},
                        {"name": "Toastmasters", "color": "green"}
                    ]
                }},
                "Location": {"multi_select": {
                    "options": [
                        {"name": "Berlin", "color": "red"},
                        {"name": "Amsterdam", "color": "blue"},
                        {"name": "London", "color": "green"}
                    ]
                }},
                "Past companies": {"multi_select": {
                    "options": [
                        {"name": "AWS", "color": "red"},
                        {"name": "BCG", "color": "blue"},
                    ]
                }},
                "Level": {"select": {
                    "options": [
                        {"name": "IC", "color": "red"},
                        {"name": "Lead", "color": "blue"},
                        {"name": "Director", "color": "green"},
                        {"name": "C-level", "color": "yellow"},
                        {"name": "Founder", "color": "brown"},
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

            # Update database properties
            try:
                self.client.databases.update(
                    database_id=self.database_id,
                    properties=current_properties
                )
                logging.info(f"Updated database properties for database ID: {self.database_id}")

                # Add overdue logic if overdue not in current_properties
                if "Overdue" not in current_properties:
                    logging.info(f"Adding overdue logic to database properties")
                    current_properties["Overdue"] = {
                        'formula': {
                            'expression': 'now() > prop("Last Contacted") + duration(if(prop("Contact Schedule") == "Weekly", 7, if(prop("Contact Schedule") == "Monthly", 30, if(prop("Contact Schedule") == "Yearly", 365, 9999999))) + "days")'
                        }
                    }
                    self.client.databases.update(
                        database_id=self.database_id,
                        properties=current_properties
                    )
                    logging.info(f"Updated overdue logic successfully")
            except Exception as e:
                logging.error(f"Error updating database formula: {str(e)}")
                # Continue execution even if formula update fails
                pass
        
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
                "Name": {"title": [{"text": {"content": contact.get("Name", "Unknown")}}]},
                "Company": {"rich_text": [{"text": {"content": contact.get("Company", "")}}]},
                "Position": {"rich_text": [{"text": {"content": contact.get("Position", "")}}]},
                "Connected On": {"date": {"start": contact.get("Connected On", "")}},
            }

            # Handle LinkedIn URL separately
            linkedin_url = contact.get("LinkedIn URL")
            if linkedin_url and linkedin_url.strip():
                properties["LinkedIn URL"] = {"url": linkedin_url.strip()}

            # Remove any properties with None or empty string values
            properties = {k: v for k, v in properties.items() if v is not None and v != ""}

            self.client.pages.create(parent={"database_id": self.database_id}, properties=properties)
            logging.info(f"Added contact: {contact.get('Name', 'Unknown')}")
        except Exception as e:
            logging.error(f"Error adding contact: {str(e)}")
            # Don't raise the exception, just log it and continue

    def update_contact(self, page_id, updates):
        try:
            properties = {}
            for key, value in updates.items():
                if key == "Name":
                    properties[key] = {"title": [{"text": {"content": value or "Unknown"}}]}
                elif key == "LinkedIn URL":
                    if value and value.strip():
                        properties[key] = {"url": value.strip()}
                elif key in ["Company", "Position"]:
                    properties[key] = {"rich_text": [{"text": {"content": value or ""}}]}
            
            # Remove any properties with None or empty string values
            properties = {k: v for k, v in properties.items() if v is not None and v != ""}

            self.client.pages.update(page_id=page_id, properties=properties)
            logging.info(f"Updated contact with page ID: {page_id}")
        except Exception as e:
            logging.error(f"Error updating contact: {str(e)}")
            # Don't raise the exception, just log it and continue

    def get_all_contacts(self):
        try:
            query_post = {"database_id": self.database_id}
            results = self.client.databases.query(**query_post)
            next_cur = results.get("next_cursor")
            while results["has_more"]:
                query_post["start_cursor"] = next_cur
                db_query_ret = self.client.databases.query(
                      **query_post
                 )
                next_cur = db_query_ret["next_cursor"]
                results["results"] += db_query_ret["results"]
                if next_cur is None:
                    break
            contacts = results.get("results", [])
            logging.info(f"Retrieved {len(contacts)} contacts from the database")
            return contacts
        except Exception as e:
            logging.error(f"Error retrieving contacts: {str(e)}")
            raise
