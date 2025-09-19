import os
import json
from pyairtable import Api
from dotenv import load_dotenv

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

def decompress_applicant_data(applicant_id):
    """
    Decompress JSON data back into normalized tables
    """
    try:
        print(f"Decompressing data for applicant: {applicant_id}")
        
        # Get the applicant record with compressed JSON
        applicant_records = applicants_table.all(formula=f"{{Applicant ID}} = '{applicant_id}'")
        if not applicant_records:
            print(f"❌ No applicant found with ID: {applicant_id}")
            return False
            
        applicant_record = applicant_records[0]
        compressed_json = applicant_record['fields'].get('Compressed JSON')
        
        if not compressed_json:
            print(f"❌ No compressed JSON found for applicant: {applicant_id}")
            return False
        
        # Parse the JSON
        try:
            data = json.loads(compressed_json)
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON format: {str(e)}")
            return False
        
        # Get the Airtable record ID for the applicant (needed for linking)
        applicant_record_id = applicant_record['id']
        
        # 1. Update/Create Personal Details
        if data.get('personal'):
            personal_data = data['personal']
            # Check if personal record exists
            existing_personal = personal_table.all(formula=f"{{Applicant ID}} = '{applicant_id}'")
            
            personal_fields = {
                'Full Name': personal_data.get('name', ''),
                'Email': personal_data.get('email', ''),
                'Location': personal_data.get('location', ''),
                'LinkedIn': personal_data.get('linkedin', ''),
                'Applicant ID': [applicant_record_id]  # Link to applicant
            }
            
            if existing_personal:
                # Update existing record
                personal_table.update(existing_personal[0]['id'], personal_fields)
                print("✅ Updated personal details")
            else:
                # Create new record
                personal_table.create(personal_fields)
                print("✅ Created personal details")
        
        # 2. Update/Create Work Experience
        if data.get('experience'):
            # First, delete existing work experience records
            existing_work = work_table.all(formula=f"{{Applicant ID}} = '{applicant_id}'")
            for record in existing_work:
                work_table.delete(record['id'])
            
            # Create new work experience records
            for exp in data['experience']:
                work_fields = {
                    'Company': exp.get('company', ''),
                    'Title': exp.get('title', ''),
                    'Start': exp.get('start', ''),
                    'End': exp.get('end', ''),
                    'Technologies': exp.get('technologies', ''),
                    'Applicant ID': [applicant_record_id]  # Link to applicant
                }
                work_table.create(work_fields)
            print(f"✅ Created {len(data['experience'])} work experience records")
        
        # 3. Update/Create Salary Preferences
        if data.get('salary'):
            salary_data = data['salary']
            # Check if salary record exists
            existing_salary = salary_table.all(formula=f"{{Applicant ID}} = '{applicant_id}'")
            
            # Get the actual field schema to debug
            try:
                schema = salary_table.schema()
                print("Available fields in Salary Preferences:")
                for field in schema.fields:
                    print(f"  - '{field.name}' (type: {field.type})")
            except:
                pass
            
            salary_fields = {
                'Preferred Rate': salary_data.get('preferred_rate', 0),
                'Minimum Rate': salary_data.get('minimum_rate', 0),
                'Currency': salary_data.get('currency', 'USD'),
                'Availability (hrs/wk)': salary_data.get('availability', 0),
                'Applicant ID': [applicant_record_id]  # Link to applicant
            }
            
            if existing_salary:
                # Update existing record
                salary_table.update(existing_salary[0]['id'], salary_fields)
                print("✅ Updated salary preferences")
            else:
                # Create new record
                salary_table.create(salary_fields)
                print("✅ Created salary preferences")
        
        print(f"✅ Successfully decompressed data for {applicant_id}")
        return True
        
    except Exception as e:
        print(f"❌ Error decompressing data for {applicant_id}: {str(e)}")
        return False

def decompress_all_applicants():
    """
    Decompress data for all applicants that have compressed JSON
    """
    try:
        # Get all applicants with compressed JSON
        all_applicants = applicants_table.all()
        processed = 0
        
        for applicant in all_applicants:
            applicant_id = applicant['fields'].get('Applicant ID')
            compressed_json = applicant['fields'].get('Compressed JSON')
            
            if applicant_id and compressed_json:
                if decompress_applicant_data(applicant_id):
                    processed += 1
            else:
                print(f"⚠️  Skipping applicant {applicant_id}: No compressed JSON")
        
        print(f"✅ Processed {processed} applicants")
        
    except Exception as e:
        print(f"❌ Error processing all applicants: {str(e)}")

if __name__ == "__main__":
    print("=== JSON Decompression Script ===")
    
    # Option 1: Decompress specific applicant
    # decompress_applicant_data("APP001")
    
    # Option 2: Decompress all applicants
    decompress_all_applicants()