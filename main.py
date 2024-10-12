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

        if not os.getenv("NOTION_TOKEN") or not os.getenv("NOTION_DATABASE_ID"):
            raise ValueError("NOTION_TOKEN and NOTION_DATABASE_ID must be set in the environment variables")

        notion_manager = NotionManager()
        linkedin_parser = LinkedInParser()
        contact_manager = ContactManager(notion_manager, linkedin_parser)
        cli = CLI(contact_manager)

        logging.info("Personal CRM application started")
        
        # Run the CLI
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
