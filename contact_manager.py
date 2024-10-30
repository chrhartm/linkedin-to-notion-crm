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
                contact['properties'].get('LinkedIn URL', {}).get('url'): contact
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
                        # Compare and update only if changed
                        existing_contact = existing_urls[linkedin_url]
                        if self._has_changes(existing_contact, contact):
                            self.notion_manager.update_contact(existing_contact['id'], contact)
                            logging.info(f"Updated contact: {contact.get('Name')}")
                        else:
                            logging.info(f"No changes detected for contact: {contact.get('Name')}")
                    else:
                        # Add new contact
                        self.notion_manager.add_contact(contact)
                        logging.info(f"Added new contact: {contact.get('Name')}")
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

    def _has_changes(self, existing_contact, new_contact):
        """
        Compare existing contact with new contact data to detect changes
        """
        try:
            properties = existing_contact['properties']
            
            # Compare Name
            existing_name = self._get_title_value(properties.get('Name'))
            if existing_name != new_contact.get('Name'):
                return True

            # Compare Company
            existing_company = self._get_rich_text_value(properties.get('Company'))
            if existing_company != new_contact.get('Company'):
                return True

            # Compare Position
            existing_position = self._get_rich_text_value(properties.get('Position'))
            if existing_position != new_contact.get('Position'):
                return True

            # Compare LinkedIn URL
            existing_url = properties.get('LinkedIn URL', {}).get('url')
            if existing_url != new_contact.get('LinkedIn URL'):
                return True

            # Compare Connected On date
            existing_date = self._get_date_value(properties.get('Connected On'))
            if existing_date != new_contact.get('Connected On'):
                return True

            return False
        except Exception as e:
            logging.warning(f"Error comparing contacts, assuming changes needed: {str(e)}")
            return True

    def _get_title_value(self, prop):
        """Extract value from a title property"""
        if not prop or 'title' not in prop:
            return ''
        return prop['title'][0]['text']['content'] if prop['title'] else ''

    def _get_rich_text_value(self, prop):
        """Extract value from a rich_text property"""
        if not prop or 'rich_text' not in prop:
            return ''
        return prop['rich_text'][0]['text']['content'] if prop['rich_text'] else ''

    def _get_date_value(self, prop):
        """Extract value from a date property"""
        if not prop or 'date' not in prop:
            return ''
        return prop['date']['start'] if prop['date'] else ''

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
