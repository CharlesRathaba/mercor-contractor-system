import os
import json
import time
import google.generativeai as genai
from pyairtable import Api
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Airtable API
api = Api(os.getenv('AIRTABLE_API_TOKEN'))
base = api.base(os.getenv('AIRTABLE_BASE_ID'))
applicants_table = base.table('Applicants')

# Configure Gemini
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')

def create_evaluation_prompt(json_data):
    """
    Create a structured prompt for LLM evaluation
    """
    prompt = f"""You are a recruiting analyst. Given this JSON applicant profile, do four things:

APPLICANT DATA:
{json.dumps(json_data, indent=2)}

Please analyze this candidate and provide:

1. A concise 75-word summary highlighting their key strengths and background
2. Rate overall candidate quality from 1-10 (higher is better) based on experience, skills, and market value
3. List any data gaps or inconsistencies you notice
4. Suggest up to three follow-up questions to clarify gaps or assess fit

Return your response in exactly this format:
Summary: [your 75-word summary here]
Score: [integer from 1-10]
Issues: [comma-separated list or 'None']
Follow-Ups:
• [question 1]
• [question 2] 
• [question 3]"""

    return prompt

def call_gemini_api(prompt, retries=0):
    """
    Make API call to Gemini with retry logic
    """
    if not GEMINI_API_KEY:
        raise Exception("GEMINI_API_KEY not found in environment variables")
    
    try:
        # Generate response
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=500,
            )
        )
        
        if response.text:
            return {
                'success': True,
                'content': response.text.strip(),
                'tokens_used': len(response.text.split()) + len(prompt.split())  # Rough estimate
            }
        else:
            return {
                'success': False,
                'error': "No response text from Gemini",
                'content': None
            }
        
    except Exception as e:
        if retries < 3:
            wait_time = (2 ** retries)  # 1s, 2s, 4s
            print(f"⚠️  API call failed, retrying in {wait_time}s... (attempt {retries + 1}/3)")
            print(f"   Error: {str(e)}")
            time.sleep(wait_time)
            return call_gemini_api(prompt, retries + 1)
        else:
            return {
                'success': False,
                'error': f"API call failed after 3 retries: {str(e)}",
                'content': None
            }

def parse_llm_response(llm_content):
    """
    Parse the structured LLM response into components
    """
    try:
        lines = llm_content.split('\n')
        
        summary = ""
        score = 0
        issues = "None"
        follow_ups = []
        
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith("Summary:"):
                summary = line.replace("Summary:", "").strip()
            elif line.startswith("Score:"):
                score_str = line.replace("Score:", "").strip()
                try:
                    score = int(score_str)
                except ValueError:
                    score = 5  # Default fallback
            elif line.startswith("Issues:"):
                issues = line.replace("Issues:", "").strip()
            elif line.startswith("Follow-Ups:"):
                current_section = "follow_ups"
            elif line.startswith("•") and current_section == "follow_ups":
                follow_ups.append(line.replace("•", "").strip())
        
        return {
            'summary': summary,
            'score': score,
            'issues': issues,
            'follow_ups': follow_ups
        }
        
    except Exception as e:
        print(f"⚠️  Error parsing LLM response: {str(e)}")
        return {
            'summary': "Error parsing LLM response",
            'score': 5,
            'issues': "Response parsing failed",
            'follow_ups': []
        }

def evaluate_applicant_with_gemini(applicant_record):
    """
    Evaluate a single applicant using Gemini
    """
    try:
        applicant_id = applicant_record['fields'].get('Applicant ID')
        compressed_json = applicant_record['fields'].get('Compressed JSON')
        
        if not compressed_json:
            print(f"⚠️  No compressed JSON for {applicant_id}")
            return False
        
        print(f"🤖 Evaluating {applicant_id} with Gemini...")
        
        # Parse the JSON data
        try:
            json_data = json.loads(compressed_json)
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON for {applicant_id}: {str(e)}")
            return False
        
        # Create prompt and call Gemini
        prompt = create_evaluation_prompt(json_data)
        llm_result = call_gemini_api(prompt)
        
        if not llm_result['success']:
            print(f"❌ Gemini API call failed for {applicant_id}: {llm_result['error']}")
            return False
        
        print(f"✅ Gemini response received (~{llm_result['tokens_used']} tokens)")
        
        # Parse the LLM response
        parsed_result = parse_llm_response(llm_result['content'])
        
        # Format follow-ups for Airtable
        follow_ups_text = '\n'.join([f"• {q}" for q in parsed_result['follow_ups']])
        
        # Update the Applicants table
        update_data = {
            'LLM Summary': parsed_result['summary'],
            'LLM Score': parsed_result['score'],
            'LLM Follow-Ups': follow_ups_text
        }
        
        applicants_table.update(applicant_record['id'], update_data)
        
        print(f"✅ Updated {applicant_id}")
        print(f"   Summary: {parsed_result['summary'][:60]}...")
        print(f"   Score: {parsed_result['score']}/10")
        print(f"   Follow-ups: {len(parsed_result['follow_ups'])} questions")
        
        return True
        
    except Exception as e:
        print(f"❌ Error evaluating {applicant_id}: {str(e)}")
        return False

def process_all_applicants():
    """
    Process all applicants that have compressed JSON but no LLM evaluation
    """
    try:
        print("=== Gemini LLM Evaluation & Enrichment ===")
        
        # Get all applicants
        all_applicants = applicants_table.all()
        
        processed = 0
        
        for applicant in all_applicants:
            applicant_id = applicant['fields'].get('Applicant ID')
            compressed_json = applicant['fields'].get('Compressed JSON')
            existing_summary = applicant['fields'].get('LLM Summary')
            
            # Skip if no data or already processed
            if not applicant_id or not compressed_json:
                print(f"⚠️  Skipping {applicant_id}: Missing compressed JSON")
                continue
                
            if existing_summary:
                print(f"⚠️  Skipping {applicant_id}: Already has LLM evaluation")
                continue
            
            # Process with Gemini
            if evaluate_applicant_with_gemini(applicant):
                processed += 1
                
            # Small delay to be respectful to the API
            time.sleep(2)
        
        print(f"\n=== Gemini Processing Complete ===")
        print(f"Processed: {processed} applicants")
        
    except Exception as e:
        print(f"❌ Error in Gemini processing: {str(e)}")

def process_specific_applicant(applicant_id):
    """
    Process a specific applicant by ID
    """
    try:
        applicants = applicants_table.all(formula=f"{{Applicant ID}} = '{applicant_id}'")
        if not applicants:
            print(f"❌ Applicant {applicant_id} not found")
            return
            
        evaluate_applicant_with_gemini(applicants[0])
        
    except Exception as e:
        print(f"❌ Error processing {applicant_id}: {str(e)}")

if __name__ == "__main__":
    print("=== Gemini LLM Evaluation Script ===")
    
    # Check if API key is configured
    if not GEMINI_API_KEY:
        print("❌ Please add GEMINI_API_KEY to your .env file")
        print("   Get your API key from: https://aistudio.google.com/app/apikey")
        exit(1)
    
    # Option 1: Process all applicants
    process_all_applicants()
    
    # Option 2: Process specific applicant
    # process_specific_applicant("APP001")