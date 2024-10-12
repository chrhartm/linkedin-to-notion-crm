import pandas as pd
import logging

class LinkedInParser:
    def parse_linkedin_export(self, file_path):
        try:
            # Parse the LinkedIn data export CSV file
            df = pd.read_csv(file_path)
            contacts = []

            for _, row in df.iterrows():
                contact = {
                    "Name": f"{row['First Name']} {row['Last Name']}".strip(),
                    "Email": row.get("Email Address", ""),
                    "Phone": row.get("Phone Numbers", ""),
                    "Company": row.get("Company", ""),
                    "Position": row.get("Position", ""),
                    "Field of Work": row.get("Industry", "Unknown"),
                    "Last Contacted": row.get("Last Date of Contact", "1970-01-01"),
                    "Contact Schedule": "Monthly",  # Set a default schedule
                }
                contacts.append(contact)

            logging.info(f"Successfully parsed {len(contacts)} contacts from LinkedIn export")
            return contacts
        except Exception as e:
            logging.error(f"Error parsing LinkedIn export: {str(e)}")
            raise
