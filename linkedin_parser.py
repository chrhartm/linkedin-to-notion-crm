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
                # Convert all values to strings and handle NaN/None values
                contact = {
                    "Name": f"{str(row[actual_columns.get('First Name', '')]).strip() if pd.notna(row[actual_columns.get('First Name', '')]) else ''} {str(row[actual_columns.get('Last Name', '')]).strip() if pd.notna(row[actual_columns.get('Last Name', '')]) else ''}".strip(),
                    "LinkedIn URL": str(row.get(actual_columns.get('Profile URL', ''), '')).strip() if pd.notna(row.get(actual_columns.get('Profile URL', ''), '')) else '',
                    "Company": str(row.get(actual_columns.get('Company', ''), '')).strip() if pd.notna(row.get(actual_columns.get('Company', ''), '')) else '',
                    "Position": str(row.get(actual_columns.get('Position', ''), '')).strip() if pd.notna(row.get(actual_columns.get('Position', ''), '')) else '',
                    "Connected On": self._format_date(str(row.get(actual_columns.get('Connected On', ''), '')).strip() if pd.notna(row.get(actual_columns.get('Connected On', ''), '')) else ''),
                }
                contacts.append(contact)

            logging.info(f"Successfully parsed {len(contacts)} contacts from LinkedIn export")
            return contacts
        except Exception as e:
            logging.error(f"Error parsing LinkedIn export: {str(e)}")
            raise

    def _format_date(self, date_str):
        """Format the date string to a consistent format"""
        if not date_str:
            return ''
        
        # Split by space and reverse to get components
        parts = date_str.split(' ')
        if len(parts) != 3:
            return date_str
            
        # Map month names to numbers
        month_map = {
            'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
            'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
            'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
        }
        
        day, month, year = parts
        month = month_map.get(month, month)
        return f"{year}-{month}-{day}"
