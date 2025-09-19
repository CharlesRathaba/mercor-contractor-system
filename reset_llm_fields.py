import os
from pyairtable import Api
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Airtable API
api = Api(os.getenv('AIRTABLE_API_TOKEN'))
base = api.base(os.getenv('AIRTABLE_BASE_ID'))
applicants_table = base.table('Applicants')

def reset_llm_fields():
    """
    Reset all LLM fields to empty for all applicants
    """
    try:
        print("=== Resetting LLM Fields ===")
        
        # Get all applicants
        all_applicants = applicants_table.all()
        
        reset_count = 0
        
        for applicant in all_applicants:
            applicant_id = applicant['fields'].get('Applicant ID')
            has_llm_data = (applicant['fields'].get('LLM Summary') or 
                          applicant['fields'].get('LLM Score') or 
                          applicant['fields'].get('LLM Follow-Ups'))
            
            if has_llm_data:
                print(f"🧹 Clearing LLM data for {applicant_id}")
                
                # Clear all LLM fields
                update_data = {
                    'LLM Summary': None,
                    'LLM Score': None,
                    'LLM Follow-Ups': None
                }
                
                applicants_table.update(applicant['id'], update_data)
                reset_count += 1
                print(f"✅ Cleared {applicant_id}")
            else:
                print(f"⚠️  {applicant_id}: No LLM data to clear")
        
        print(f"\n=== Reset Complete ===")
        print(f"Reset {reset_count} applicants")
        
    except Exception as e:
        print(f"❌ Error resetting fields: {str(e)}")

def reset_specific_applicant(applicant_id):
    """
    Reset LLM fields for a specific applicant
    """
    try:
        applicants = applicants_table.all(formula=f"{{Applicant ID}} = '{applicant_id}'")
        if not applicants:
            print(f"❌ Applicant {applicant_id} not found")
            return
            
        applicant = applicants[0]
        
        update_data = {
            'LLM Summary': None,
            'LLM Score': None,
            'LLM Follow-Ups': None
        }
        
        applicants_table.update(applicant['id'], update_data)
        print(f"✅ Cleared LLM data for {applicant_id}")
        
    except Exception as e:
        print(f"❌ Error resetting {applicant_id}: {str(e)}")

if __name__ == "__main__":
    print("=== LLM Fields Reset Script ===")
    
    # Option 1: Reset all applicants
    reset_llm_fields()
    
    # Option 2: Reset specific applicant
    # reset_specific_applicant("APP001")