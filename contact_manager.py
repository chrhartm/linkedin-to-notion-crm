import logging

class ContactManager:
    def __init__(self, notion_manager, linkedin_parser):
        self.notion_manager = notion_manager
        self.linkedin_parser = linkedin_parser

    def _is_valid_contact(self, contact):
        """Check if the contact has any meaningful data."""
        required_fields = ['Name', 'Company', 'Position', 'LinkedIn URL']
        has_valid_data = any(
            contact.get(field) and str(contact.get(field)).strip()
            for field in required_fields
        )
        
        if not has_valid_data:
            field_values = {field: contact.get(field, 'N/A') for field in required_fields}
            logging.info(f"Skipping empty contact with fields: {field_values}")
        
        return has_valid_data

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
        try:
            properties = existing_contact['properties']
            
            def normalize(s):
                if not s:
                    return ''
                # Convert to string, strip whitespace, and lowercase for case-insensitive comparison
                return str(s).strip().lower()
            
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
                logging.debug(f"  Existing: '{existing_value}' -> '{existing_normalized}'")
                logging.debug(f"  New: '{new_value}' -> '{new_normalized}'")
                
                if existing_normalized != new_normalized:
                    logging.info(f"Change detected in {field_name}:")
                    logging.info(f"  Existing: '{existing_value}'")
                    logging.info(f"  New: '{new_value}'")
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

    def get_all_contacts(self):
        """Retrieve all contacts from Notion database."""
        try:
            contacts = self.notion_manager.get_all_contacts()
            logging.info(f"Retrieved {len(contacts)} contacts from Notion database.")
            return contacts
        except Exception as e:
            logging.error(f"Error retrieving contacts: {str(e)}")
            raise
