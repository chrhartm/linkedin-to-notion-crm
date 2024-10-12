import os
import logging
from dotenv import load_dotenv
from notion_manager import NotionManager
from linkedin_parser import LinkedInParser
from contact_manager import ContactManager
from cli import CLI

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    try:
        load_dotenv()

        notion_token = os.getenv("NOTION_TOKEN")
        notion_database_id = os.getenv("NOTION_DATABASE_ID")

        if not notion_token or not notion_database_id:
            raise ValueError("NOTION_TOKEN and NOTION_DATABASE_ID must be set in the environment variables")

        notion_manager = NotionManager()
        linkedin_parser = LinkedInParser()
        contact_manager = ContactManager(notion_manager, linkedin_parser)

        # Ensure the Notion database exists
        notion_manager.ensure_database_exists()

        logging.info("Personal CRM application started")
        
        # Print database properties
        print("\nCurrent Database Properties:")
        notion_manager.print_database_properties()
        
        # Print available commands
        print("\nAvailable commands:")
        print("  sync <linkedin_export_path> - Sync LinkedIn contacts to Notion database")
        print("  update_contact <page_id> <json_updates> - Update a specific contact")
        print("  list_contacts - List all contacts in the Notion database")
        print("  export_contacts <output_file_path> - Export all contacts to a CSV file")
        print("  search_contacts <query> - Search contacts by name or company")
        print("  list_overdue - List all overdue contacts")
        print("  update_last_contacted <page_id> <date> - Update the last contacted date for a contact")
        print("  print_db_properties - Print the current database properties")
        print("  quit - Exit the CLI")
        
        # Run the CLI
        cli = CLI(contact_manager)
        cli.cmdloop()

    except ValueError as ve:
        logging.error(f"Configuration error: {str(ve)}")
        print(f"Configuration error: {str(ve)}")
        print("Please make sure you've set the NOTION_TOKEN and NOTION_DATABASE_ID environment variables.")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}")
        print(f"An unexpected error occurred: {str(e)}")
        print("Please check the logs for more information.")

if __name__ == "__main__":
    main()
