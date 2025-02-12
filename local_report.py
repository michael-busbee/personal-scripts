import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

# Load email credentials from .env file
load_dotenv(dotenv_path='.env')

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Set up logging
logging.basicConfig(
    filename='logs/local_report.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def scrape_county_info(county):
    """
    Scrapes useful local information for the given county.
    For demonstration purposes, this function uses placeholder URLs and logic.
    Replace the URL and scraping logic as needed for your target websites.
    """
    # Map county names to their (assumed) news or local info URLs
    county_urls = {
        "Shenandoah VA": "https://www.shenandoahcountyva.gov/news",
        "Frederick VA": "https://www.frederickcountyva.gov/news",
        "Winchester City VA": "https://www.winchesterva.gov/news"
    }
    url = county_urls.get(county)
    results = []

    if url:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                # Attempt to get news items or local info; adjust selectors accordingly.
                # For example, assume items are in divs with class "news-item"
                news_items = soup.find_all(class_="news-item")
                for item in news_items:
                    title = item.find('h2').get_text(strip=True) if item.find('h2') else "No Title"
                    summary = item.find('p').get_text(strip=True) if item.find('p') else "No Summary"
                    results.append((title, summary))
            else:
                logging.error(f"Failed to retrieve data from {url} (Status code: {response.status_code})")
        except Exception as e:
            logging.error(f"Error scraping {county} info: {e}")

    # If scraping returns no results, use placeholder/dummy data.
    if not results:
        if county == "Shenandoah VA":
            results = [
                ("Community Event", "Local farmers market this Saturday at the town square."),
                ("Government Notice", "Budget meeting scheduled for next Tuesday in City Hall."),
                ("Alert", "Road closure on Main St. due to maintenance work.")
            ]
        elif county == "Frederick VA":
            results = [
                ("Local News", "New art exhibit opening at the regional gallery."),
                ("Event", "Annual county fair happening next weekend."),
                ("Notice", "Recycling center hours have changed effective immediately.")
            ]
        elif county == "Winchester City VA":
            results = [
                ("City Update", "New park opening in downtown Winchester."),
                ("Traffic Alert", "Major road reconstruction announced for Memorial Boulevard."),
                ("Community Event", "Local theater group hosting a play this Sunday.")
            ]
    return results

def generate_html_email_report(county_data):
    """
    Constructs a responsive HTML email report with separate sections for each county.
    county_data should be a dictionary in the format:
      { "County Name": [ (Category, Detail), ... ], ... }
    """
    html = f"""\
<html>
  <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <style>
      body {{
        font-family: Arial, sans-serif;
        margin: 0;
        padding: 0;
        background-color: #f4f4f4;
      }}
      .container {{
        width: 90%;
        max-width: 700px;
        margin: auto;
        background-color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
      }}
      h1 {{
        color: #333333;
      }}
      h2 {{
        color: #2b6cb0;
        border-bottom: 2px solid #eee;
        padding-bottom: 5px;
      }}
      table {{
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 30px;
      }}
      th, td {{
        border: 1px solid #dddddd;
        padding: 10px;
        text-align: left;
      }}
      th {{
        background-color: #f2f2f2;
      }}
      .data-row:nth-child(even) {{
        background-color: #f9f9f9;
      }}
      @media only screen and (max-width: 600px) {{
        .container {{
          width: 100%;
          padding: 10px;
        }}
      }}
    </style>
  </head>
  <body>
    <div class="container">
      <h1>Local Information Report</h1>
    """
    # Generate a section per county
    for county, info_list in county_data.items():
        html += f"<h2>{county}</h2>"
        html += """<table>
          <tr>
            <th>Category</th>
            <th>Details</th>
          </tr>
        """
        for category, detail in info_list:
            html += f"<tr class='data-row'><td>{category}</td><td>{detail}</td></tr>"
        html += "</table>"
    html += """\
    </div>
  </body>
</html>
"""
    return html

def send_email(html_content: str) -> None:
    """Send email report"""
    sender = os.getenv("GMAIL_SENDER")
    receiver = os.getenv("GMAIL_RECEIVER")
    app_password = os.getenv("GOOGLE_APP_PASSWORD")

    if not all([sender, receiver, app_password]):
        logger.error("Email credentials not configured")
        return

    subject = "County Information Report"
    msg = MIMEMultipart("alternative")
    msg["From"] = sender
    msg["To"] = receiver
    msg["Subject"] = subject
    msg.attach(MIMEText(html_content, "html"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender, app_password)
        server.sendmail(sender, receiver, msg.as_string())
        server.quit()
        print("Email sent successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")

def main():
    # Read the list of counties from counties.txt
    try:
        with open("counties.txt", "r") as f:
            counties = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"Error reading counties.txt: {e}")
        return

    county_data = {}
    
    # Scrape (or simulate) local information for each county
    for county in counties:
        print(f"Scraping local information for {county}...")
        info = scrape_county_info(county)
        county_data[county] = info

    html_body = generate_html_email_report(county_data)

    send_email(html_body)

if __name__ == "__main__":
    main() 