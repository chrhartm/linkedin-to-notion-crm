import pandas as pd

class LinkedInParser:
    def parse_linkedin_export(self, file_path):
        # Parse the LinkedIn data export CSV file
        df = pd.read_csv(file_path)
        contacts = []

        for _, row in df.iterrows():
            contact = {
                "Name": f"{row['First Name']} {row['Last Name']}",
                "Email": row["Email Address"],
                "Phone": row["Phone Numbers"],
                "Company": row["Company"],
                "Position": row["Position"],
                "Field of Work": "Unknown",  # LinkedIn export doesn't provide this directly
                "Last Contacted": "1970-01-01",  # Set a default date
                "Contact Schedule": "Monthly",  # Set a default schedule
            }
            contacts.append(contact)

        return contacts
