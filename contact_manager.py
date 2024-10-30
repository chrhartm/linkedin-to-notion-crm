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
            
            # Create lookup by LinkedIn URL
            existing_urls = {
                contact['properties'].get('LinkedIn URL', {}).get('url'): contact['id']
                for contact in existing_contacts
                if contact['properties'].get('LinkedIn URL', {}).get('url')
            }

            print(f"Found {len(existing_contacts)} existing contacts in Notion")
            
            # Track sync errors
            sync_errors = []

            # Sync LinkedIn contacts to Notion database
            for contact in linkedin_contacts:
                try:
                    linkedin_url = contact.get('LinkedIn URL')
                    if linkedin_url in existing_urls:
                        # Update existing contact
                        self.notion_manager.update_contact(existing_urls[linkedin_url], contact)
                    else:
                        # Add new contact
                        self.notion_manager.add_contact(contact)
                except Exception as e:
                    error_msg = f"Error syncing contact {contact.get('Name', 'Unknown')}: {str(e)}"
                    logging.error(error_msg)
                    sync_errors.append(error_msg)

            if sync_errors:
                error_summary = "\n".join(sync_errors)
                raise Exception(f"Encountered errors while syncing contacts:\n{error_summary}")

            logging.info(f"Synced {len(linkedin_contacts)} contacts to Notion database.")
        except Exception as e:
            logging.error(f"Error syncing contacts: {str(e)}")
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
