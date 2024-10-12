from notion_client import Client
from datetime import datetime, timedelta
import logging

class NotionManager:
    def __init__(self, token, page_id):
        self.client = Client(auth=token)
        self.page_id = page_id
        self.database_id = None
        self.ensure_database_exists()

    def ensure_database_exists(self):
        try:
            search_results = self.client.search(
                query="CRM Contacts",
                filter={
                    "property": "object",
                    "value": "database"
                },
                parent={
                    "type": "page_id",
                    "page_id": self.page_id
                }
            ).get("results")

            if search_results:
                self.database_id = search_results[0]["id"]
                logging.info(f"Connected to existing database with ID: {self.database_id}")
            else:
                logging.info("Database not found. Creating a new one.")
                self.create_database()
        except Exception as e:
            logging.error(f"Error while checking for existing database: {str(e)}")
            self.create_database()

    def create_database(self):
        properties = {
            "Name": {"title": {}},
            "Email": {"email": {}},
            "Phone": {"phone_number": {}},
            "Company": {"rich_text": {}},
            "Position": {"rich_text": {}},
            "Field of Work": {"select": {}},
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
            new_database = self.client.databases.create(
                parent={"type": "page_id", "page_id": self.page_id},
                title=[{"type": "text", "text": {"content": "CRM Contacts"}}],
                properties=properties
            )
            self.database_id = new_database["id"]
            logging.info(f"New database created with ID: {self.database_id}")
        except Exception as e:
            raise ValueError(f"Failed to create database. Error: {str(e)}")

    def add_contact(self, contact):
        self.client.pages.create(
            parent={"database_id": self.database_id},
            properties={
                "Name": {"title": [{"text": {"content": contact["Name"]}}]},
                "Email": {"email": contact["Email"]},
                "Phone": {"phone_number": contact["Phone"]},
                "Company": {"rich_text": [{"text": {"content": contact["Company"]}}]},
                "Position": {"rich_text": [{"text": {"content": contact["Position"]}}]},
                "Field of Work": {"select": {"name": contact["Field of Work"]}},
                "Last Contacted": {"date": {"start": contact["Last Contacted"]}},
                "Contact Schedule": {"select": {"name": contact["Contact Schedule"]}},
                "Overdue": {"checkbox": False},
            }
        )

    def update_contact(self, page_id, updates):
        properties = {}
        for key, value in updates.items():
            if key == "Name":
                properties[key] = {"title": [{"text": {"content": value}}]}
            elif key == "Email":
                properties[key] = {"email": value}
            elif key == "Phone":
                properties[key] = {"phone_number": value}
            elif key in ["Company", "Position"]:
                properties[key] = {"rich_text": [{"text": {"content": value}}]}
            elif key == "Field of Work":
                properties[key] = {"select": {"name": value}}
            elif key == "Last Contacted":
                properties[key] = {"date": {"start": value}}
            elif key == "Contact Schedule":
                properties[key] = {"select": {"name": value}}
            elif key == "Overdue":
                properties[key] = {"checkbox": value}

        self.client.pages.update(page_id=page_id, properties=properties)

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

        for contact in contacts:
            properties = contact.get("properties", {})
            last_contacted = properties.get("Last Contacted", {}).get("date", {}).get("start")
            schedule = properties.get("Contact Schedule", {}).get("select", {}).get("name")
            
            if last_contacted:
                last_contacted = datetime.strptime(last_contacted, "%Y-%m-%d").date()
                days_since_contact = (today - last_contacted).days

                overdue = False
                if schedule == "Weekly" and days_since_contact > 7:
                    overdue = True
                elif schedule == "Monthly" and days_since_contact > 30:
                    overdue = True
                elif schedule == "Quarterly" and days_since_contact > 90:
                    overdue = True
                elif schedule == "Yearly" and days_since_contact > 365:
                    overdue = True

                self.update_contact(contact["id"], {"Overdue": overdue})