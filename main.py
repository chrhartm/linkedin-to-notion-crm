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
        notion_page_id = os.getenv("NOTION_PAGE_ID")

        if not notion_token or not notion_page_id:
            raise ValueError("NOTION_TOKEN and NOTION_PAGE_ID must be set in the environment variables")

        notion_manager = NotionManager(notion_token, notion_page_id)
        linkedin_parser = LinkedInParser()
        contact_manager = ContactManager(notion_manager, linkedin_parser)
        cli = CLI(contact_manager)

        logging.info("Personal CRM application started")
        
        # Test commands
        test_commands = [
            "help",
            "list_contacts",
            "update_overdue",
            "quit"
        ]
        
        for cmd in test_commands:
            print(f"\nExecuting command: {cmd}")
            cli.onecmd(cmd)

    except ValueError as ve:
        logging.error(f"Configuration error: {str(ve)}")
        print(f"Configuration error: {str(ve)}")
        print("Please make sure you've set the NOTION_TOKEN and NOTION_PAGE_ID environment variables.")
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        print(f"An error occurred: {str(e)}")
        print("Please check the logs for more information.")

if __name__ == "__main__":
    main()
