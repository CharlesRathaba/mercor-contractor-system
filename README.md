# **Mercor Airtable Exercise: Contractor Application System**

## **Overview**

This system provides a complete contractor application management solution using Airtable as the data layer with Python automation scripts. The system collects multi-table application data, compresses it into JSON for storage, automatically shortlists qualified candidates, and uses AI (Google Gemini) for evaluation and enrichment.

## **System Architecture**

### **Database Schema**

**5 interconnected Airtable tables:**

1. **Applicants** (Parent Table)

   * `Applicant ID` (Primary, Single line text) \- Unique identifier  
   * `Compressed JSON` (Long text) \- Serialized application data  
   * `Shortlist Status` (Single select) \- Pending/Shortlisted/Not Shortlisted  
   * `LLM Summary` (Long text) \- AI-generated candidate summary  
   * `LLM Score` (Number) \- AI quality score (1-10)  
   * `LLM Follow-Ups` (Long text) \- AI-suggested interview questions  
2. **Personal Details** (One-to-one with Applicants)

   * `Full Name` (Primary, Single line text)  
   * `Email` (Email)  
   * `Location` (Single line text)  
   * `LinkedIn` (URL)  
   * `Applicant ID` (Link to Applicants)  
3. **Work Experience** (One-to-many with Applicants)

   * `Experience ID` (Primary, Autonumber)  
   * `Company` (Single line text)  
   * `Title` (Single line text)  
   * `Start` (Date)  
   * `End` (Date)  
   * `Technologies` (Long text)  
   * `Applicant ID` (Link to Applicants)  
4. **Salary Preferences** (One-to-one with Applicants)

   * `Salary ID` (Primary, Autonumber)  
   * `Preferred Rate` (Number, Currency)  
   * `Minimum Rate` (Number, Currency)  
   * `Currency` (Single select)  
   * `Availability (hrs/wk)` (Number)  
   * `Applicant ID` (Link to Applicants)  
5. **Shortlisted Leads** (Auto-populated)

   * `Lead ID` (Primary, Autonumber)  
   * `Applicant` (Link to Applicants)  
   * `Compressed JSON` (Long text) \- Copy of application data  
   * `Score Reason` (Long text) \- Explanation of qualification  
   * `Created At` (Created time) \- Auto-populated timestamp

## **Core Automation Scripts**

### **1\. JSON Compression (`json_compression.py`)**

**Purpose:** Aggregates data from linked tables into a single JSON object for efficient storage and processing.

**Key Features:**

* Fetches data from Personal Details, Work Experience, and Salary Preferences tables  
* Combines into structured JSON format  
* Updates Applicants table with compressed data  
* Handles multiple work experience records  
* Adds timestamp for tracking

**JSON Structure:**

{  
  "personal": {  
    "name": "John Smith",  
    "email": "john.smith@email.com",  
    "location": "New York, NY",  
    "linkedin": "https://linkedin.com/in/johnsmith"  
  },  
  "experience": \[  
    {  
      "company": "Google",  
      "title": "Software Engineer",  
      "start": "2024-07-11",  
      "end": "2025-02-03",  
      "technologies": "Python, JavaScript, React"  
    }  
  \],  
  "salary": {  
    "preferred\_rate": 96,  
    "minimum\_rate": 80,  
    "currency": "USD",  
    "availability": 30  
  },  
  "compressed\_at": "2025-09-19T22:43:08.877146"  
}

**Usage:**

python json\_compression.py

### **2\. JSON Decompression (`json_decompression.py`)**

**Purpose:** Restores normalized table structure from compressed JSON when edits are needed.

**Key Features:**

* Reads compressed JSON from Applicants table  
* Recreates/updates records in child tables  
* Handles one-to-one and one-to-many relationships  
* Maintains referential integrity  
* Upserts existing records rather than duplicating

**Usage:**

python json\_decompression.py

### **3\. Shortlist Automation (`shortlist_automation.py`)**

**Purpose:** Automatically identifies and shortlists qualified candidates based on predefined criteria.

**Qualification Criteria:**

* **Experience:** ≥4 years total OR worked at Tier-1 company  
* **Compensation:** Preferred rate ≤$100 USD/hour AND availability ≥20 hrs/week  
* **Location:** Must be in US, Canada, UK, Germany, or India

**Tier-1 Companies:** Google, Meta, OpenAI, Microsoft, Apple, Amazon, Netflix, Tesla, Stripe, Uber, Airbnb, SpaceX, DeepMind, Anthropic, GitHub, GitLab

**Process:**

1. Evaluates each applicant against all criteria  
2. Creates Shortlisted Leads record for qualified candidates  
3. Updates Shortlist Status in Applicants table  
4. Provides detailed reasoning for each decision

**Usage:**

python shortlist\_automation.py

### **4\. LLM Evaluation (`gemini_llm_evaluation.py`)**

**Purpose:** Uses Google Gemini AI to provide qualitative analysis and enrichment of applications.

**AI Analysis Provides:**

* **75-word summary** highlighting key strengths and background  
* **Quality score (1-10)** based on experience, skills, and market value  
* **Issue identification** noting data gaps or inconsistencies  
* **Follow-up questions** to clarify gaps or assess cultural fit

**Key Features:**

* Integration with Google Gemini 1.5 Flash (free tier)  
* Retry logic with exponential backoff  
* Structured prompt engineering  
* Response parsing and validation  
* Budget-conscious token usage

**Security:**

* API key stored in environment variables  
* No hardcoded credentials  
* Rate limiting respect

**Usage:**

python gemini\_llm\_evaluation.py

## **Setup Instructions**

### **1\. Environment Setup**

Create `.env` file:

AIRTABLE\_API\_TOKEN=your\_airtable\_token  
AIRTABLE\_BASE\_ID=your\_base\_id  
GEMINI\_API\_KEY=your\_gemini\_api\_key

### **2\. Install Dependencies**

pip install pyairtable requests python-dotenv google-generativeai

### **3\. API Keys**

**Airtable API Token:**

1. Visit [airtable.com/create/tokens](https://airtable.com/create/tokens)  
2. Create token with `data.records:read`, `data.records:write`, `schema.bases:read` scopes  
3. Grant access to your specific base

**Gemini API Key:**

1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)  
2. Sign in and create API key (free tier available)

### **4\. Airtable Base Setup**

1. Create base with 5 tables as specified in schema  
2. Set up proper field types and relationships  
3. Create forms for data collection (one per child table)  
4. Configure linking between tables via Applicant ID

## **Application Workflow**

### **Data Collection**

1. Create Applicant ID in main table  
2. Fill Personal Details form  
3. Fill Work Experience form (multiple entries allowed)  
4. Fill Salary Preferences form

### **Automated Processing**

1. **Compression:** `json_compression.py` creates unified JSON  
2. **Shortlisting:** `shortlist_automation.py` evaluates qualification criteria  
3. **AI Analysis:** `gemini_llm_evaluation.py` provides qualitative assessment

### **Data Management**

* **Decompression:** `json_decompression.py` restores table structure for editing  
* **Reset:** `reset_llm_fields.py` clears AI evaluations for re-processing

## **Customization Options**

### **Shortlist Criteria Modification**

Edit `shortlist_automation.py` constants:

TIER\_1\_COMPANIES \= \['Google', 'Meta', ...\]  \# Add/remove companies  
ACCEPTED\_LOCATIONS \= \['US', 'Canada', ...\]  \# Modify location rules

Modify evaluation logic in `evaluate_candidate()` function for different rules.

### **LLM Prompt Customization**

Edit `create_evaluation_prompt()` in `gemini_llm_evaluation.py` to:

* Change analysis focus areas  
* Modify output format  
* Adjust evaluation criteria  
* Add industry-specific requirements

### **Field Extensions**

Add new fields to tables and update corresponding scripts:

1. Update schema in Airtable  
2. Modify compression/decompression field mappings  
3. Update shortlist evaluation criteria if needed  
4. Enhance LLM prompts with new data points

## **Error Handling & Monitoring**

### **Built-in Safeguards**

* **API Rate Limiting:** Exponential backoff retry logic  
* **Data Validation:** JSON parsing error handling  
* **Field Mapping:** Graceful handling of missing/renamed fields  
* **Transaction Safety:** Individual record processing prevents batch failures

### **Logging**

All scripts provide detailed console output including:

* Processing status for each applicant  
* Error messages with context  
* Success confirmations  
* Performance metrics (token usage, processing counts)

### **Troubleshooting**

**Common Issues:**

1. **Field Name Mismatches:** Check exact field names in Airtable  
2. **API Rate Limits:** Built-in retry logic handles temporary limits  
3. **Missing Data:** Scripts skip records with insufficient data  
4. **JSON Format Errors:** Validation prevents corrupted data processing

## **Security & Best Practices**

### **Data Protection**

* API keys stored in environment variables only  
* No credentials in source code  
* Airtable permissions scoped to minimum required access

### **Performance Optimization**

* Batch processing where possible  
* Intelligent skip logic for already-processed records  
* Token usage monitoring for cost control  
* Minimal API calls through caching logic

### **Scalability**

* Individual record processing prevents memory issues  
* Configurable batch sizes  
* Rate limiting compliance  
* Modular script design for easy extension

## **Testing & Validation**

### **Test Data Requirements**

Create test applicant with:

* Complete personal details  
* Multiple work experiences  
* Realistic salary preferences  
* Geographic location in accepted regions

### **Validation Checklist**

* \[ \] Forms collect data correctly  
* \[ \] Table relationships function properly  
* \[ \] JSON compression captures all fields  
* \[ \] Decompression restores exact data  
* \[ \] Shortlist criteria evaluate correctly  
* \[ \] LLM integration provides quality responses  
* \[ \] Error handling works for edge cases

## **Future Enhancements**

### **Potential Improvements**

1. **Web Interface:** Replace Airtable forms with custom application portal  
2. **Advanced Scoring:** Multi-factor scoring algorithms  
3. **Integration APIs:** Connect with job boards or HR systems  
4. **Analytics Dashboard:** Application pipeline metrics  
5. **Automated Communications:** Email notifications for status changes  
6. **Document Processing:** Resume parsing and skill extraction  
7. **Interview Scheduling:** Calendar integration for qualified candidates

### **Architecture Evolution**

* Microservices architecture for enterprise scale  
* Real-time processing with webhooks  
* Advanced caching strategies  
* Multi-tenant support for different clients  
* Audit logging and compliance features

## **Conclusion**

This system demonstrates a complete applicant tracking workflow with modern automation, AI integration, and scalable architecture. The combination of Airtable's user-friendly interface with Python automation provides both accessibility for non-technical users and powerful processing capabilities for complex business logic.
