import requests
from bs4 import BeautifulSoup
import time
import random
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pandas as pd
import re
from openai import OpenAI
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI client
client = OpenAI(api_key=openai_api_key)

# Update keywords to be more specific
keywords = [
    "Security Operations Center Analyst",
    "SOC Analyst",
    "Security Analyst",
]

# Define headers to mimic a real browser
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}

def setup_google_sheets():
    """Set up Google Sheets API connection"""
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive',
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive.file'
    ]
    
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            'jobsearch-450623-cddcfd864bc2.json', scope)
        client = gspread.authorize(creds)
        print("Successfully authorized with Google")
        
        # List all available spreadsheets
        available_sheets = client.list_spreadsheet_files()
        print("Available spreadsheets:", [sheet['name'] for sheet in available_sheets])
        
        sheet = client.open('JobListings').sheet1
        print("Successfully opened the sheet")
        return sheet, client
        
    except Exception as e:
        print(f"Error in setup_google_sheets: {type(e).__name__}: {str(e)}")
        raise

def clean_description(text):
    """Clean up job description text by removing excess whitespace and normalizing line breaks"""
    if not text:
        return ""
    
    # Replace multiple newlines with a single newline
    text = re.sub(r'\n\s*\n', '\n', text)
    
    # Replace multiple spaces with a single space
    text = re.sub(r'\s+', ' ', text)
    
    # Strip whitespace from beginning and end
    text = text.strip()
    
    return text

def build_job_evaluation_prompt(description):
    """Build a prompt for GPT-4 to evaluate job listings"""
    return f"""Please evaluate this job posting based on the following criteria:
1. It must be a tier 1/entry-level Security Operations Center (SOC) Analyst position
2. It must NOT require any security clearance
3. It must be either a remote position OR located in VA, MD, or DC
4. It must be a full-time position
5. It must not require previous experience in a SOC role.

Please respond with only 'YES' if the job meets ALL criteria or 'NO' if it fails any criteria.

Job Description:
{description}"""

def evaluate_job_with_gpt4(description):
    """Use GPT-4 to evaluate if a job posting meets our criteria"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that evaluates job postings."},
                {"role": "user", "content": build_job_evaluation_prompt(description)}
            ]
        )
        result = response.choices[0].message.content.strip().upper()
        return result == 'YES'
    except Exception as e:
        print(f"Error in GPT-4 evaluation: {str(e)}")
        return False

def search_linkedin():
    """Search LinkedIn for job listings"""
    job_listings = []
    
    # Location parameters for LinkedIn search
    locations = [
        "remote",
        "Winchester, Virginia, United States"  # LinkedIn will handle the radius
    ]
    
    for keyword in keywords:
        for location in locations:
            try:
                # Construct LinkedIn search URL with location parameter
                url = f"https://www.linkedin.com/jobs/search/?keywords={keyword.replace(' ', '%20')}&location={location.replace(' ', '%20')}&distance=75"
                response = requests.get(url, headers=headers)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                for link in soup.find_all('a', href=True):
                    if '/jobs/view/' in link['href']:
                        title = link.get_text().strip() if link.get_text() else "No title available"
                        job_url = link['href']
                        
                        try:
                            job_response = requests.get(job_url, headers=headers)
                            job_soup = BeautifulSoup(job_response.text, 'html.parser')
                            description = job_soup.find('div', class_='description__text').get_text()
                            description = clean_description(description)
                            
                            # Use GPT-4 to evaluate the job
                            if evaluate_job_with_gpt4(description):
                                job_listings.append({
                                    'title': title,
                                    'url': job_url,
                                    'keyword': keyword,
                                    'description': description,
                                    'date_found': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    'location': location
                                })
                                print(f"Found matching job: {title}")
                            else:
                                print(f"Skipping job that doesn't meet criteria: {title}")
                                
                        except Exception as e:
                            print(f"Error getting job description: {str(e)}")
                
                time.sleep(random.uniform(2, 5))
            except Exception as e:
                print(f"Error in LinkedIn search for {keyword} in {location}: {str(e)}")
    return job_listings

def filter_security_clearance(df):
    """Filter out jobs requiring security clearance"""
    clearance_keywords = [
        r'security clearance',
        r'secret clearance',
        r'top secret',
        r'ts/sci',
        r'clearance required',
        r'must be able to obtain clearance'
    ]
    
    pattern = '|'.join(clearance_keywords)
    mask = ~df['description'].str.lower().str.contains(pattern, regex=True, na=False)
    filtered_df = df[mask].copy()
    
    print(f"Filtered out {len(df) - len(filtered_df)} jobs requiring security clearance")
    return filtered_df

def update_spreadsheet(sheet, df):
    """Update Google Sheets with job listings"""
    try:
        existing_data = pd.DataFrame(sheet.get_all_records())
        
        if len(existing_data) == 0:
            headers = ['Date Found', 'Search Keyword', 'Job Title', 'URL', 'Description', 'Location']
            sheet.append_row(headers)
            rows_to_add = df[['date_found', 'keyword', 'title', 'url', 'description', 'location']].values.tolist()
        else:
            new_jobs = df[~df['url'].isin(existing_data['URL'])]
            rows_to_add = new_jobs[['date_found', 'keyword', 'title', 'url', 'description', 'location']].values.tolist()
        
        if rows_to_add:
            sheet.append_rows(rows_to_add)
            print(f"Added {len(rows_to_add)} new job listings to the sheet")
        else:
            print("No new job listings to add")
            
    except Exception as e:
        print(f"Error updating spreadsheet: {str(e)}")
        raise

def main():
    print("Starting LinkedIn job search...")
    
    try:
        sheet, client = setup_google_sheets()
        print("Successfully connected to Google Sheets")
    except Exception as e:
        print(f"Error connecting to Google Sheets: {str(e)}")
        return
    
    job_listings = search_linkedin()
    print(f"Found {len(job_listings)} matching job listings")
    
    df = pd.DataFrame(job_listings)
    if not df.empty:
        df = df.drop_duplicates(subset=['url'])
        print(f"Removed {len(job_listings) - len(df)} duplicate listings")
        
        try:
            update_spreadsheet(sheet, df)
        except Exception as e:
            print(f"Error updating spreadsheet: {str(e)}")
        
        print("\nProcessed Job Listings:")
        print(f"Total found: {len(job_listings)}")
        print(f"After removing duplicates: {len(df)}")
        print(f"Final listings added: {len(df)}")
    else:
        print("No matching jobs found")

if __name__ == "__main__":
    main() 