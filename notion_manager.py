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
                    {"name": "Weekly", "color": "blue"},
                    {"name": "Monthly", "color": "green"},
                    {"name": "Quarterly", "color": "yellow"},
                    {"name": "Yearly", "color": "red"}
                ]
            }},
            "Overdue": {"checkbox": {}},
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

    def add_contact(self, contact):
        properties = {
            "Name": {"title": [{"text": {"content": contact.get("Name", "")}}]},
            "LinkedIn URL": {"url": contact.get("LinkedIn URL") or None},
            "Company": {"rich_text": [{"text": {"content": contact.get("Company", "")}}]},
            "Position": {"rich_text": [{"text": {"content": contact.get("Position", "")}}]},
            "Industry": {"select": {"name": contact.get("Industry", "Other")}},
            "Field of Work": {"select": {"name": contact.get("Field of Work", "Other")}},
            "Last Contacted": {"date": {"start": contact.get("Last Contacted", "1970-01-01")}},
            "Contact Schedule": {"select": {"name": contact.get("Contact Schedule", "Monthly")}},
            "Overdue": {"checkbox": False},
        }

        try:
            self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties
            )
            logging.info(f"Added contact: {contact.get('Name', 'Unknown')}")
        except Exception as e:
            logging.error(f"Error adding contact {contact.get('Name', 'Unknown')}: {str(e)}")
            raise

    def update_contact(self, page_id, updates):
        properties = {}
        for key, value in updates.items():
            if key == "Name":
                properties[key] = {"title": [{"text": {"content": value}}]}
            elif key == "LinkedIn URL":
                properties[key] = {"url": value if value else None}
            elif key in ["Company", "Position"]:
                properties[key] = {"rich_text": [{"text": {"content": value}}]}
            elif key in ["Industry", "Field of Work"]:
                properties[key] = {"select": {"name": value}}
            elif key == "Last Contacted":
                properties[key] = {"date": {"start": value}}
            elif key == "Contact Schedule":
                properties[key] = {"select": {"name": value}}
            elif key == "Overdue":
                properties[key] = {"checkbox": value}

        try:
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
            logging.error(f"Error fetching contacts: {str(e)}")
            return []

    def update_overdue_status(self):
        contacts = self.get_all_contacts()
        today = datetime.now().date()
        updated_count = 0
        skipped_count = 0

        for contact in contacts:
            try:
                properties = contact.get("properties", {})
                last_contacted = properties.get("Last Contacted", {}).get("date", {})
                schedule = properties.get("Contact Schedule", {}).get("select", {})
                
                if not last_contacted or not schedule:
                    logging.warning(f"Skipping contact {contact['id']} due to missing Last Contacted or Contact Schedule")
                    skipped_count += 1
                    continue

                last_contacted_date = last_contacted.get("start")
                schedule_name = schedule.get("name")

                if not last_contacted_date or not schedule_name:
                    logging.warning(f"Skipping contact {contact['id']} due to invalid Last Contacted or Contact Schedule")
                    skipped_count += 1
                    continue

                last_contacted_date = datetime.strptime(last_contacted_date, "%Y-%m-%d").date()
                days_since_contact = (today - last_contacted_date).days

                overdue = False
                if schedule_name == "Weekly" and days_since_contact > 7:
                    overdue = True
                elif schedule_name == "Monthly" and days_since_contact > 30:
                    overdue = True
                elif schedule_name == "Quarterly" and days_since_contact > 90:
                    overdue = True
                elif schedule_name == "Yearly" and days_since_contact > 365:
                    overdue = True

                self.update_contact(contact["id"], {"Overdue": overdue})
                updated_count += 1

            except Exception as e:
                logging.error(f"Error updating overdue status for contact {contact['id']}: {str(e)}")
                skipped_count += 1

        logging.info(f"Updated overdue status for {updated_count} contacts. Skipped {skipped_count} contacts.")
