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
                    self._process_single_contact(contact, existing_contacts)
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

    def _process_single_contact(self, contact, existing_contacts):
        """Process a single contact, either updating existing or adding new."""
        try:
            linkedin_url = contact.get('LinkedIn URL')
            existing_contact = None
            
            # Find existing contact by LinkedIn URL
            for existing in existing_contacts:
                if existing['properties'].get('LinkedIn URL', {}).get('url') == linkedin_url:
                    existing_contact = existing
                    break

            if existing_contact:
                # Compare and update only if changed
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
            logging.error(f"Error processing contact {contact.get('Name', 'Unknown')}: {str(e)}")
            raise

    def _has_changes(self, existing_contact, new_contact):
        """
        Compare existing contact with new contact data to detect changes with improved logging
        and string normalization.
        """
        try:
            properties = existing_contact['properties']
            
            # Helper function to normalize strings
            def normalize(s):
                return str(s).strip() if s else ''
            
            # Compare each field with logging
            fields_to_compare = [
                ('Name', self._get_title_value(properties.get('Name')), new_contact.get('Name')),
                ('Company', self._get_rich_text_value(properties.get('Company')), new_contact.get('Company')),
                ('Position', self._get_rich_text_value(properties.get('Position')), new_contact.get('Position')),
                ('LinkedIn URL', properties.get('LinkedIn URL', {}).get('url'), new_contact.get('LinkedIn URL')),
                ('Connected On', self._get_date_value(properties.get('Connected On')), new_contact.get('Connected On'))
            ]
            
            logging.debug(f"Comparing contact: {new_contact.get('Name', 'Unknown')}")
            
            for field_name, existing_value, new_value in fields_to_compare:
                existing_normalized = normalize(existing_value)
                new_normalized = normalize(new_value)
                
                logging.debug(f"Comparing {field_name}:")
                logging.debug(f"  Existing: '{existing_normalized}'")
                logging.debug(f"  New: '{new_normalized}'")
                
                if existing_normalized != new_normalized:
                    logging.info(f"Change detected in {field_name}: '{existing_normalized}' -> '{new_normalized}'")
                    return True
                    
            logging.info("No changes detected, skipping update")
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
