import cmd
import json

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

    def do_update_overdue(self, arg):
        "Update overdue status for all contacts"
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
        for contact in contacts:
            print(f"Name: {contact['properties']['Name']['title'][0]['text']['content']}")
            print(f"Email: {contact['properties']['Email']['email']}")
            print(f"Company: {contact['properties']['Company']['rich_text'][0]['text']['content']}")
            print(f"Overdue: {contact['properties']['Overdue']['checkbox']}")
            print("---")

    def do_quit(self, arg):
        "Exit the CLI"
        print("Goodbye!")
        return True

    def default(self, line):
        print(f"Command not recognized: {line}")
        return cmd.Cmd.default(self, line)

    def run(self):
        self.cmdloop()
