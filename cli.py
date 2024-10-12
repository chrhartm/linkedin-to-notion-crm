import cmd
import json
import logging

class CLI(cmd.Cmd):
    intro = "Welcome to the Personal CRM CLI. Type 'help' to list commands."
    prompt = "(CRM) "

    def __init__(self, contact_manager):
        super().__init__()
        self.contact_manager = contact_manager

    def do_sync(self, arg):
        "Sync LinkedIn contacts to Notion database: sync <linkedin_export_path>"
        if not arg:
            print("Please provide the path to the LinkedIn export file.")
            return
        self.contact_manager.sync_contacts(arg)
        self.contact_manager.update_overdue_status()

    def do_update_contact(self, arg):
        "Update a specific contact: update_contact <page_id> <json_updates>"
        args = arg.split(" ", 1)
        if len(args) != 2:
            print("Usage: update_contact <page_id> <json_updates>")
            return
        
        page_id, updates_json = args
        try:
            updates = json.loads(updates_json)
            self.contact_manager.update_contact(page_id, updates)
        except json.JSONDecodeError:
            print("Invalid JSON format for updates.")

    def do_list_contacts(self, arg):
        "List all contacts in the Notion database"
        contacts = self.contact_manager.get_all_contacts()
        if not contacts:
            print("No contacts found in the database.")
            return
        for contact in contacts:
            try:
                properties = contact.get('properties', {})
                print(f"Contact ID: {contact.get('id', 'N/A')}")
                for prop_name, prop_value in properties.items():
                    print(f"{prop_name}: {self._format_property(prop_value)}")
                print("---")
            except Exception as e:
                logging.error(f"Error processing contact: {str(e)}")
                print(f"Error processing a contact: {str(e)}. Please check the logs for more information.")

    def _format_property(self, prop):
        if isinstance(prop, dict):
            if 'title' in prop:
                return prop['title'][0]['text']['content'] if prop['title'] else 'N/A'
            elif 'rich_text' in prop:
                return prop['rich_text'][0]['text']['content'] if prop['rich_text'] else 'N/A'
            elif 'select' in prop:
                return prop['select']['name'] if prop['select'] else 'N/A'
            elif 'url' in prop:
                return prop['url']
            elif 'checkbox' in prop:
                return 'Yes' if prop['checkbox'] else 'No'
            elif 'date' in prop:
                return prop['date']['start'] if prop['date'] else 'N/A'
        return str(prop)

    def do_quit(self, arg):
        "Exit the CLI"
        print("Goodbye!")
        return True

    def default(self, line):
        print(f"Command not recognized: {line}")
        return cmd.Cmd.default(self, line)
