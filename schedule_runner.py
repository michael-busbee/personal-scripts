#!/usr/bin/python3
import time
import subprocess
import logging
from datetime import datetime
import pytz
import os

# Set up logging
logging.basicConfig(
    filename='/root/personal-scripts/scheduler.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def run_scripts():
    """Run both scripts and log results"""
    try:
        logging.info("Starting scripts execution")
        
        # Change to scripts directory
        os.chdir('/root/personal-scripts')
        
        # Run stock-watcher
        logging.info("Running stock-watcher.py")
        subprocess.run(['/usr/bin/python3', 'stock-watcher.py'], check=True)
        logging.info("Completed stock-watcher.py")
        
        # Run county_report
        logging.info("Running county_report.py")
        subprocess.run(['/usr/bin/python3', 'county_report.py'], check=True)
        logging.info("Completed county_report.py")
        
        logging.info("All scripts completed successfully")
        
    except Exception as e:
        logging.error(f"Error running scripts: {str(e)}")

def is_execution_time():
    """Check if it's time to run the scripts (9 AM Eastern)"""
    eastern = pytz.timezone('America/New_York')
    now = datetime.now(eastern)
    return now.hour == 9 and now.minute == 0

def main():
    logging.info("Scheduler starting up...")
    
    # Log startup information
    eastern = pytz.timezone('America/New_York')
    now = datetime.now(eastern)
    logging.info(f"Current time: {now}")
    logging.info("Scheduler will run scripts at 9:00 AM Eastern time daily")
    
    last_run_date = None
    
    while True:
        try:
            now = datetime.now(eastern)
            current_date = now.date()
            
            # Run if it's 9 AM and we haven't run today
            if is_execution_time() and current_date != last_run_date:
                logging.info(f"Starting daily run at {now}")
                run_scripts()
                last_run_date = current_date
                logging.info(f"Completed daily run at {datetime.now(eastern)}")
            
            # Sleep for 30 seconds before next check
            time.sleep(30)
            
        except Exception as e:
            logging.error(f"Error in main loop: {str(e)}")
            time.sleep(60)  # Wait a minute before retrying if there's an error

if __name__ == "__main__":
    main()
