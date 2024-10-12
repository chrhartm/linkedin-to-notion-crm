class ContactManager:
    def __init__(self, notion_manager, linkedin_parser):
        self.notion_manager = notion_manager
        self.linkedin_parser = linkedin_parser

    def sync_contacts(self, linkedin_export_path):
        # Sync LinkedIn contacts to Notion database
        linkedin_contacts = self.linkedin_parser.parse_linkedin_export(linkedin_export_path)
        
        for contact in linkedin_contacts:
            self.notion_manager.add_contact(contact)

        print(f"Synced {len(linkedin_contacts)} contacts to Notion database.")

    def update_overdue_status(self):
        # Update overdue status for all contacts
        self.notion_manager.update_overdue_status()
        print("Updated overdue status for all contacts.")

    def update_contact(self, page_id, updates):
        # Update a specific contact
        self.notion_manager.update_contact(page_id, updates)
        print(f"Updated contact with page ID: {page_id}")

    def get_all_contacts(self):
        # Retrieve all contacts from Notion database
        return self.notion_manager.get_all_contacts()
