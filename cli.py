import cmd
import json
import logging
import csv
from datetime import datetime

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

    def do_export_contacts(self, arg):
        "Export all contacts to a CSV file: export_contacts <output_file_path>"
        if not arg:
            print("Please provide the output file path for the CSV.")
            return
        
        contacts = self.contact_manager.get_all_contacts()
        if not contacts:
            print("No contacts found in the database.")
            return

        try:
            with open(arg, 'w', newline='') as csvfile:
                fieldnames = ['Name', 'LinkedIn URL', 'Company', 'Position', 'Industry', 'Field of Work', 'Last Contacted', 'Contact Schedule', 'Overdue']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for contact in contacts:
                    properties = contact.get('properties', {})
                    row = {
                        'Name': self._format_property(properties.get('Name')),
                        'LinkedIn URL': self._format_property(properties.get('LinkedIn URL')),
                        'Company': self._format_property(properties.get('Company')),
                        'Position': self._format_property(properties.get('Position')),
                        'Industry': self._format_property(properties.get('Industry')),
                        'Field of Work': self._format_property(properties.get('Field of Work')),
                        'Last Contacted': self._format_property(properties.get('Last Contacted')),
                        'Contact Schedule': self._format_property(properties.get('Contact Schedule')),
                        'Overdue': self._format_property(properties.get('Overdue'))
                    }
                    writer.writerow(row)

            print(f"Contacts exported successfully to {arg}")
        except Exception as e:
            logging.error(f"Error exporting contacts: {str(e)}")
            print(f"Error exporting contacts: {str(e)}. Please check the logs for more information.")

    def do_search_contacts(self, arg):
        "Search contacts by name or company: search_contacts <query>"
        if not arg:
            print("Please provide a search query.")
            return

        contacts = self.contact_manager.get_all_contacts()
        results = []

        for contact in contacts:
            properties = contact.get('properties', {})
            name = self._format_property(properties.get('Name', '')).lower()
            company = self._format_property(properties.get('Company', '')).lower()
            
            if arg.lower() in name or arg.lower() in company:
                results.append(contact)

        if not results:
            print("No matching contacts found.")
            return

        print(f"Found {len(results)} matching contacts:")
        for contact in results:
            properties = contact.get('properties', {})
            print(f"Name: {self._format_property(properties.get('Name'))}")
            print(f"Company: {self._format_property(properties.get('Company'))}")
            print(f"Position: {self._format_property(properties.get('Position'))}")
            print("---")

    def do_list_overdue(self, arg):
        "List all overdue contacts"
        contacts = self.contact_manager.get_all_contacts()
        overdue_contacts = [contact for contact in contacts if self._format_property(contact['properties'].get('Overdue')) == 'true']

        if not overdue_contacts:
            print("No overdue contacts found.")
            return

        print(f"Found {len(overdue_contacts)} overdue contacts:")
        for contact in overdue_contacts:
            properties = contact.get('properties', {})
            print(f"Name: {self._format_property(properties.get('Name'))}")
            print(f"Company: {self._format_property(properties.get('Company'))}")
            print(f"Last Contacted: {self._format_property(properties.get('Last Contacted'))}")
            print(f"Contact Schedule: {self._format_property(properties.get('Contact Schedule'))}")
            print("---")

    def do_update_last_contacted(self, arg):
        "Update the last contacted date for a contact: update_last_contacted <page_id> <date>"
        args = arg.split()
        if len(args) != 2:
            print("Usage: update_last_contacted <page_id> <date>")
            return

        page_id, date_str = args
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d").date()
            updates = {"Last Contacted": date.isoformat()}
            self.contact_manager.update_contact(page_id, updates)
            print(f"Updated last contacted date for contact {page_id} to {date_str}")
        except ValueError:
            print("Invalid date format. Please use YYYY-MM-DD.")
        except Exception as e:
            print(f"Error updating contact: {str(e)}")

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
            elif 'formula' in prop:
                return str(prop['formula'].get('boolean', 'N/A'))
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
