import os
import json
from pyairtable import Api
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Initialize Airtable API
api = Api(os.getenv('AIRTABLE_API_TOKEN'))
base = api.base(os.getenv('AIRTABLE_BASE_ID'))

# Table references
applicants_table = base.table('Applicants')
personal_table = base.table('Personal Details')
work_table = base.table('Work Experience')
salary_table = base.table('Salary Preferences')

def compress_applicant_data(applicant_id):
    """
    Compress data from linked tables into a single JSON object
    """
    try:
        print(f"Processing applicant: {applicant_id}")
        
        # Get personal details
        personal_records = personal_table.all(formula=f"{{Applicant ID}} = '{applicant_id}'")
        personal_data = {}
        if personal_records:
            record = personal_records[0]['fields']
            personal_data = {
                "name": record.get('Full Name', ''),
                "email": record.get('Email', ''),
                "location": record.get('Location', ''),
                "linkedin": record.get('LinkedIn', '')
            }
        
        # Get work experience (multiple records possible)
        work_records = work_table.all(formula=f"{{Applicant ID}} = '{applicant_id}'")
        experience_data = []
        for record in work_records:
            fields = record['fields']
            exp_entry = {
                "company": fields.get('Company', ''),
                "title": fields.get('Title', ''),
                "start": fields.get('Start', ''),
                "end": fields.get('End', ''),
                "technologies": fields.get('Technologies', '')
            }
            experience_data.append(exp_entry)
        
        # Get salary preferences
        salary_records = salary_table.all(formula=f"{{Applicant ID}} = '{applicant_id}'")
        salary_data = {}
        if salary_records:
            record = salary_records[0]['fields']
            # Try different possible field names for availability
            availability = (record.get('Availability (hrs/wk)', 0) or
                          record.get('Availability', 0))
            
            salary_data = {
                "preferred_rate": record.get('Preferred Rate', 0),
                "minimum_rate": record.get('Minimum Rate', 0),
                "currency": record.get('Currency', 'USD'),
                "availability": availability
            }
        
        # Create compressed JSON
        compressed_data = {
            "personal": personal_data,
            "experience": experience_data,
            "salary": salary_data,
            "compressed_at": datetime.now().isoformat()
        }
        
        # Convert to JSON string
        json_string = json.dumps(compressed_data, indent=2)
        
        # Update the Applicants table with compressed JSON
        applicant_records = applicants_table.all(formula=f"{{Applicant ID}} = '{applicant_id}'")
        if applicant_records:
            record_id = applicant_records[0]['id']
            applicants_table.update(record_id, {
                'Compressed JSON': json_string
            })
            print(f"✅ Successfully compressed data for {applicant_id}")
            print(f"JSON Preview:\n{json_string}")
        else:
            print(f"❌ No applicant found with ID: {applicant_id}")
            
        return json_string
        
    except Exception as e:
        print(f"❌ Error compressing data for {applicant_id}: {str(e)}")
        return None

def compress_all_applicants():
    """
    Compress data for all applicants in the system
    """
    try:
        # Get all applicants
        all_applicants = applicants_table.all()
        print(f"Found {len(all_applicants)} applicants to process")
        
        for applicant in all_applicants:
            applicant_id = applicant['fields'].get('Applicant ID')
            if applicant_id:
                compress_applicant_data(applicant_id)
            else:
                print(f"⚠️  Skipping applicant with missing ID: {applicant['id']}")
                
    except Exception as e:
        print(f"❌ Error processing all applicants: {str(e)}")

if __name__ == "__main__":
    print("=== JSON Compression Script ===")
    
    # Option 1: Compress specific applicant
    # compress_applicant_data("APP001")
    
    # Option 2: Compress all applicants
    compress_all_applicants()