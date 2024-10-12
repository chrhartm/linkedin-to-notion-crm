import logging

class ContactManager:
    def __init__(self, notion_manager, linkedin_parser):
        self.notion_manager = notion_manager
        self.linkedin_parser = linkedin_parser

    def sync_contacts(self, linkedin_export_path):
        try:
            # Parse LinkedIn contacts
            linkedin_contacts = self.linkedin_parser.parse_linkedin_export(linkedin_export_path)
            
            # Get existing contacts from Notion
            existing_contacts = self.notion_manager.get_all_contacts()
            existing_linkedin_urls = set(contact['properties']['LinkedIn URL']['url'] for contact in existing_contacts if contact['properties']['LinkedIn URL']['url'])
            
            # Sync LinkedIn contacts to Notion database
            for contact in linkedin_contacts:
                if contact['LinkedIn URL'] not in existing_linkedin_urls:
                    self.notion_manager.add_contact(contact)
                else:
                    # Update existing contact
                    existing_contact = next(c for c in existing_contacts if c['properties']['LinkedIn URL']['url'] == contact['LinkedIn URL'])
                    self.notion_manager.update_contact(existing_contact['id'], contact)

            logging.info(f"Synced {len(linkedin_contacts)} contacts to Notion database.")
        except Exception as e:
            logging.error(f"Error syncing contacts: {str(e)}")
            raise

    def update_overdue_status(self):
        try:
            # Update overdue status for all contacts
            self.notion_manager.update_overdue_status()
            logging.info("Updated overdue status for all contacts.")
        except Exception as e:
            logging.error(f"Error updating overdue status: {str(e)}")
            raise

    def update_contact(self, page_id, updates):
        try:
            # Update a specific contact
            self.notion_manager.update_contact(page_id, updates)
            logging.info(f"Updated contact with page ID: {page_id}")
        except Exception as e:
            logging.error(f"Error updating contact: {str(e)}")
            raise

    def get_all_contacts(self):
        try:
            # Retrieve all contacts from Notion database
            contacts = self.notion_manager.get_all_contacts()
            logging.info(f"Retrieved {len(contacts)} contacts from Notion database.")
            return contacts
        except Exception as e:
            logging.error(f"Error retrieving contacts: {str(e)}")
            raise
