import pandas as pd
import logging

class LinkedInParser:
    def parse_linkedin_export(self, file_path='Connections.csv'):
        try:
            # Skip the first three lines as they contain export notes
            df = pd.read_csv(file_path, skiprows=3)
            contacts = []

            # Define mappings for expected column names
            column_mappings = {
                'First Name': ['First Name', 'First_Name', 'FirstName'],
                'Last Name': ['Last Name', 'Last_Name', 'LastName'],
                'Email Address': ['Email Address', 'Email_Address', 'EmailAddress', 'Email'],
                'Company': ['Company', 'Organization', 'Company Name'],
                'Position': ['Position', 'Job Title', 'Title'],
                'Connected On': ['Connected On', 'Connection Date', 'Connected_On'],
                'Profile URL': ['URL', 'LinkedIn URL', 'Public Profile URL']
            }

            # Find the actual column names in the CSV
            actual_columns = {}
            for expected_col, possible_names in column_mappings.items():
                found_col = next((col for col in df.columns if col in possible_names), None)
                if found_col:
                    actual_columns[expected_col] = found_col
                else:
                    logging.warning(f"Column '{expected_col}' not found in the CSV. Using default values.")

            for _, row in df.iterrows():
                contact = {
                    "Name": f"{row[actual_columns.get('First Name', '')]} {row[actual_columns.get('Last Name', '')]}".strip(),
                    "LinkedIn URL": row.get(actual_columns.get('Profile URL', ''), ''),
                    "Company": row.get(actual_columns.get('Company', ''), ''),
                    "Position": row.get(actual_columns.get('Position', ''), ''),
                    "Connected On": str.join("-",row.get(actual_columns.get('Connected On', ''), '').split(" ")[::-1]).replace("Jan", "01").replace("Feb", "02").replace("Mar", "03").replace("Apr", "04").replace("May", "05").replace("Jun", "06").replace("Jul", "07").replace("Aug", "08").replace("Sep", "09").replace("Oct", "10").replace("Nov", "11").replace("Dec", "12"),
                }
                contacts.append(contact)

            logging.info(f"Successfully parsed {len(contacts)} contacts from LinkedIn export")
            return contacts
        except Exception as e:
            logging.error(f"Error parsing LinkedIn export: {str(e)}")
            raise
