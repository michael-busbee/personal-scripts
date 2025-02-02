import os
from dotenv import load_dotenv
import yfinance as yf
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
from datetime import datetime, timedelta

load_dotenv(dotenv_path='.env')

def analyze_stock(stock):
    try:
        # Download roughly one year of historical data.
        data = yf.download(stock, period="1y", progress=False)
    except Exception as e:
        print(f"Error downloading data for {stock}: {e}")
        return None

    # Ensure we have enough data
    if data.empty or len(data) < 200:
        print(f"Not enough data for {stock}.")
        return None

    # Calculate moving averages
    data['MA50'] = data['Close'].rolling(window=50).mean()
    data['MA200'] = data['Close'].rolling(window=200).mean()

    # Remove rows where the moving averages are NaN and then take the last 10 days.
    data = data.dropna(subset=['MA50', 'MA200'])
    last10 = data.tail(10)
    
    if len(last10) < 2:
        print(f"Not enough valid days for {stock}.")
        return None

    # Determine the crossover by comparing the first and last days of the 10-day window.
    start_diff = last10['MA50'].iloc[0] - last10['MA200'].iloc[0]
    end_diff = last10['MA50'].iloc[-1] - last10['MA200'].iloc[-1]

    if start_diff < 0 and end_diff > 0:
        # 50-day MA has crossed above 200-day MA: Buy signal.
        return "Buy"
    elif start_diff > 0 and end_diff < 0:
        # 50-day MA has crossed below 200-day MA: Sell signal.
        return "Sell"
    else:
        return None

def send_email(buys, sells, sender, receiver, smtp_server, smtp_port, login, password):
    """
    Compose and send an email with the buy and sell lists.
    """
    subject = "Daily Stock Signals"
    body_lines = []

    if buys:
        body_lines.append("Buy Signals:")
        body_lines.extend(buys)
    else:
        body_lines.append("No Buy signals today.")

    body_lines.append("")  # Blank line between sections

    if sells:
        body_lines.append("Sell Signals:")
        body_lines.extend(sells)
    else:
        body_lines.append("No Sell signals today.")

    body = "\n".join(body_lines)

    # Create email message
    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = receiver
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(login, password)
        server.sendmail(sender, receiver, msg.as_string())
        server.quit()
        print("Email sent successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")

def main():
    try:
        with open("stocks.txt", "r") as f:
            stocks = [line.strip() for line in f if line.strip() != ""]
    except Exception as e:
        print(f"Error reading stocks.txt: {e}")
        return

    buy_list = []
    sell_list = []

    for stock in stocks:
        print(f"Analyzing {stock}...")
        signal = analyze_stock(stock)
        if signal == "Buy":
            buy_list.append(stock)
        elif signal == "Sell":
            sell_list.append(stock)


    # NOTE: Update the following email settings with your actual values.
    sender = os.getenv("GOOGLE_ACCOUNT")
    receiver = os.getenv("GOOGLE_ACCOUNT")
    smtp_server = "smtp.gmail.com"  # e.g., "smtp.gmail.com" for Gmail
    smtp_port = 587  # Port 587 for TLS (or 465 for SSL)
    login = os.getenv("GOOGLE_ACCOUNT")
    app_password = os.getenv("GOOGLE_APP_PASSWORD")

    send_email(buy_list, sell_list, sender, receiver, smtp_server, smtp_port, login, password)

if __name__ == "__main__":
    # This loop will wait until a target time each day (e.g., 6:00 PM) to run.
    target_hour = 18   # 6 PM (24-hour clock)
    target_minute = 0  # 0 minutes

    while True:
        now = datetime.now()
        # Create today's target datetime.
        target_time = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
        
        # If the target time today has already passed, schedule for tomorrow.
        if now >= target_time:
            target_time += timedelta(days=1)

        sleep_seconds = (target_time - now).total_seconds()
        print(f"Waiting {int(sleep_seconds)} seconds until next analysis at {target_time.strftime('%Y-%m-%d %H:%M:%S')}...")
        time.sleep(sleep_seconds)
        main()
