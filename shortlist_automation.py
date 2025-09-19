import os
import json
from pyairtable import Api
from dotenv import load_dotenv
from datetime import datetime, date

# Load environment variables
load_dotenv()

# Initialize Airtable API
api = Api(os.getenv('AIRTABLE_API_TOKEN'))
base = api.base(os.getenv('AIRTABLE_BASE_ID'))

# Table references
applicants_table = base.table('Applicants')
shortlisted_table = base.table('Shortlisted Leads')

# Shortlist criteria constants
TIER_1_COMPANIES = [
    'Google', 'Meta', 'OpenAI', 'Microsoft', 'Apple', 'Amazon', 
    'Netflix', 'Tesla', 'Stripe', 'Uber', 'Airbnb', 'SpaceX',
    'DeepMind', 'Anthropic', 'GitHub', 'GitLab'
]

ACCEPTED_LOCATIONS = [
    'US', 'USA', 'United States', 'Canada', 'UK', 'United Kingdom', 
    'Germany', 'India', 'New York', 'NYC', 'San Francisco', 'SF',
    'London', 'Berlin', 'Munich', 'Toronto', 'Vancouver', 'Mumbai',
    'Delhi', 'Bangalore', 'Hyderabad'
]

def calculate_experience_years(experience_data):
    """
    Calculate total years of experience from work history
    """
    total_years = 0
    
    for exp in experience_data:
        start_str = exp.get('start', '')
        end_str = exp.get('end', '')
        
        if not start_str:
            continue
            
        try:
            # Parse dates (format: YYYY-MM-DD)
            start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
            
            if end_str:
                end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
            else:
                # If no end date, assume current position
                end_date = date.today()
            
            # Calculate years (approximate)
            years = (end_date - start_date).days / 365.25
            total_years += years
            
        except ValueError as e:
            print(f"⚠️  Error parsing dates for {exp.get('company', 'Unknown')}: {e}")
            continue
    
    return round(total_years, 1)

def has_tier1_experience(experience_data):
    """
    Check if candidate has worked at a Tier-1 company
    """
    for exp in experience_data:
        company = exp.get('company', '').strip()
        if company in TIER_1_COMPANIES:
            return True, company
    return False, None

def check_location(location):
    """
    Check if candidate is in an accepted location
    """
    if not location:
        return False
    
    location_upper = location.upper()
    for accepted in ACCEPTED_LOCATIONS:
        if accepted.upper() in location_upper:
            return True
    return False

def evaluate_candidate(applicant_data):
    """
    Evaluate if a candidate meets shortlist criteria
    """
    try:
        data = json.loads(applicant_data['Compressed JSON'])
        
        # Initialize results
        criteria_met = {
            'experience': False,
            'compensation': False,
            'location': False
        }
        reasons = []
        
        # 1. Experience Check
        experience_data = data.get('experience', [])
        total_years = calculate_experience_years(experience_data)
        has_tier1, tier1_company = has_tier1_experience(experience_data)
        
        if total_years >= 4:
            criteria_met['experience'] = True
            reasons.append(f"Has {total_years} years of experience (≥4 required)")
        elif has_tier1:
            criteria_met['experience'] = True
            reasons.append(f"Worked at Tier-1 company: {tier1_company}")
        else:
            reasons.append(f"Insufficient experience: {total_years} years, no Tier-1 companies")
        
        # 2. Compensation Check
        salary_data = data.get('salary', {})
        preferred_rate = salary_data.get('preferred_rate', 0)
        availability = salary_data.get('availability', 0)
        currency = salary_data.get('currency', 'USD')
        
        if preferred_rate <= 100 and currency == 'USD' and availability >= 20:
            criteria_met['compensation'] = True
            reasons.append(f"Rate ${preferred_rate}/hr (≤$100) with {availability} hrs/week (≥20)")
        else:
            reasons.append(f"Compensation mismatch: ${preferred_rate}/hr {currency}, {availability} hrs/week")
        
        # 3. Location Check
        personal_data = data.get('personal', {})
        location = personal_data.get('location', '')
        
        if check_location(location):
            criteria_met['location'] = True
            reasons.append(f"Location accepted: {location}")
        else:
            reasons.append(f"Location not accepted: {location}")
        
        # Overall result
        all_criteria_met = all(criteria_met.values())
        
        return {
            'qualified': all_criteria_met,
            'criteria_met': criteria_met,
            'reasons': reasons,
            'summary': {
                'experience_years': total_years,
                'tier1_company': tier1_company,
                'rate': preferred_rate,
                'currency': currency,
                'availability': availability,
                'location': location
            }
        }
        
    except Exception as e:
        return {
            'qualified': False,
            'criteria_met': {'experience': False, 'compensation': False, 'location': False},
            'reasons': [f"Error evaluating candidate: {str(e)}"],
            'summary': {}
        }

def create_shortlisted_lead(applicant_record, evaluation_result):
    """
    Create a record in the Shortlisted Leads table
    """
    try:
        # Create the shortlisted lead record
        lead_data = {
            'Applicant': [applicant_record['id']],  # Link to the applicant
            'Compressed JSON': applicant_record['fields']['Compressed JSON'],
            'Score Reason': '\n'.join(evaluation_result['reasons']),
            # 'Created At' is auto-populated by Airtable
        }
        
        new_lead = shortlisted_table.create(lead_data)
        
        # Update the applicant's shortlist status
        applicants_table.update(applicant_record['id'], {
            'Shortlist Status': 'Shortlisted'
        })
        
        return new_lead
        
    except Exception as e:
        print(f"❌ Error creating shortlisted lead: {str(e)}")
        return None

def process_all_applicants():
    """
    Process all applicants and shortlist qualified candidates
    """
    try:
        print("=== Lead Shortlist Automation ===")
        
        # Get all applicants with compressed JSON
        all_applicants = applicants_table.all()
        
        shortlisted_count = 0
        processed_count = 0
        
        for applicant in all_applicants:
            applicant_id = applicant['fields'].get('Applicant ID')
            compressed_json = applicant['fields'].get('Compressed JSON')
            current_status = applicant['fields'].get('Shortlist Status')
            
            if not applicant_id or not compressed_json:
                print(f"⚠️  Skipping {applicant_id}: Missing data")
                continue
            
            print(f"\n--- Evaluating {applicant_id} ---")
            
            # Evaluate the candidate
            evaluation = evaluate_candidate(applicant['fields'])
            processed_count += 1
            
            # Print evaluation results
            print(f"Experience: {'✅' if evaluation['criteria_met']['experience'] else '❌'}")
            print(f"Compensation: {'✅' if evaluation['criteria_met']['compensation'] else '❌'}")
            print(f"Location: {'✅' if evaluation['criteria_met']['location'] else '❌'}")
            print(f"Overall: {'✅ QUALIFIED' if evaluation['qualified'] else '❌ NOT QUALIFIED'}")
            
            # Update shortlist status
            if evaluation['qualified']:
                if current_status != 'Shortlisted':
                    lead = create_shortlisted_lead(applicant, evaluation)
                    if lead:
                        shortlisted_count += 1
                        print(f"✅ Added to shortlist!")
                    else:
                        # Update status even if lead creation failed
                        applicants_table.update(applicant['id'], {
                            'Shortlist Status': 'Shortlisted'
                        })
                else:
                    print(f"✅ Already shortlisted")
            else:
                # Update to not shortlisted
                applicants_table.update(applicant['id'], {
                    'Shortlist Status': 'Not Shortlisted'
                })
                print(f"❌ Marked as not shortlisted")
            
            # Print reasons
            print("Reasons:")
            for reason in evaluation['reasons']:
                print(f"  • {reason}")
        
        print(f"\n=== Summary ===")
        print(f"Processed: {processed_count} applicants")
        print(f"Newly Shortlisted: {shortlisted_count}")
        
    except Exception as e:
        print(f"❌ Error processing applicants: {str(e)}")

if __name__ == "__main__":
    process_all_applicants()