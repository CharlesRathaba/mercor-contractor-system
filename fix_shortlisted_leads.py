import os
from pyairtable import Api
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Airtable API
api = Api(os.getenv('AIRTABLE_API_TOKEN'))
base = api.base(os.getenv('AIRTABLE_BASE_ID'))
applicants_table = base.table('Applicants')
shortlisted_table = base.table('Shortlisted Leads')

def check_and_fix_shortlisted_leads():
    """
    Check for applicants marked as shortlisted but missing from Shortlisted Leads table
    """
    try:
        print("=== Checking Shortlisted Leads ===")
        
        # Get all shortlisted applicants
        shortlisted_applicants = applicants_table.all(formula="{Shortlist Status} = 'Shortlisted'")
        print(f"Found {len(shortlisted_applicants)} applicants marked as shortlisted")
        
        # Get existing shortlisted leads
        existing_leads = shortlisted_table.all()
        print(f"Found {len(existing_leads)} records in Shortlisted Leads table")
        
        # Get applicant IDs that already have leads
        existing_lead_applicant_ids = []
        for lead in existing_leads:
            if 'Applicant' in lead['fields']:
                existing_lead_applicant_ids.extend(lead['fields']['Applicant'])
        
        print(f"Existing lead applicant record IDs: {existing_lead_applicant_ids}")
        
        # Create missing leads
        created = 0
        for applicant in shortlisted_applicants:
            applicant_id = applicant['fields'].get('Applicant ID')
            applicant_record_id = applicant['id']
            compressed_json = applicant['fields'].get('Compressed JSON', '')
            
            print(f"\nChecking {applicant_id} (record ID: {applicant_record_id})")
            
            # Check if this applicant already has a lead
            if applicant_record_id not in existing_lead_applicant_ids:
                print(f"  → Creating missing shortlisted lead for {applicant_id}")
                
                # Create the lead
                lead_data = {
                    'Applicant': [applicant_record_id],
                    'Compressed JSON': compressed_json,
                    'Score Reason': 'Qualified candidate meeting all shortlist criteria: experience, compensation, and location requirements.'
                }
                
                try:
                    new_lead = shortlisted_table.create(lead_data)
                    print(f"  ✅ Created lead for {applicant_id}")
                    created += 1
                except Exception as e:
                    print(f"  ❌ Error creating lead for {applicant_id}: {str(e)}")
            else:
                print(f"  ✅ {applicant_id} already has a shortlisted lead")
        
        print(f"\n=== Summary ===")
        print(f"Created {created} new shortlisted leads")
        
        # Show final counts
        final_leads = shortlisted_table.all()
        print(f"Total shortlisted leads now: {len(final_leads)}")
        
    except Exception as e:
        print(f"❌ Error checking shortlisted leads: {str(e)}")

def show_shortlisted_status():
    """
    Show current shortlist status of all applicants
    """
    try:
        print("\n=== Current Applicant Status ===")
        all_applicants = applicants_table.all()
        
        for applicant in all_applicants:
            applicant_id = applicant['fields'].get('Applicant ID', 'Unknown')
            status = applicant['fields'].get('Shortlist Status', 'No Status')
            has_json = bool(applicant['fields'].get('Compressed JSON'))
            print(f"{applicant_id}: {status} (JSON: {'✅' if has_json else '❌'})")
            
    except Exception as e:
        print(f"❌ Error showing status: {str(e)}")

if __name__ == "__main__":
    show_shortlisted_status()
    check_and_fix_shortlisted_leads()