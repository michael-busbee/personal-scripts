import os
import pandas as pd
import numpy as np
from dotenv import load_dotenv
import yfinance as yf
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


load_dotenv(dotenv_path='.env')

def get_stock_data(stock):
    """
    Downloads one year of historical data for the given stock
    """
    try:
        data = yf.download(stock, period="1y", progress=False)
        if data.empty:
            print(f"No data found for {stock}.")
            return None
        return data
    except Exception as e:
        print(f"Error downloading data for {stock}: {e}")
        return None

def technique_ma_crossover(stock, data):
    """
    Technique 1: 50-day vs 200-day Moving Average crossover.
    If the 50-day MA crosses above the 200-day MA within the last 10 days => Buy,
    If it crosses below => Sell.
    """
    if len(data) < 200:
        return None
    data = data.copy()
    data['MA50'] = data['Close'].rolling(window=50).mean()
    data['MA200'] = data['Close'].rolling(window=200).mean()
    last10 = data.tail(10)
    if len(last10) < 2:
        return None

    start_diff = last10['MA50'].iloc[0] - last10['MA200'].iloc[0]
    end_diff = last10['MA50'].iloc[-1] - last10['MA200'].iloc[-1]

    if start_diff < 0 and end_diff > 0:
        return "Buy"
    elif start_diff > 0 and end_diff < 0:
        return "Sell"
    else:
        return None

def technique_rsi(stock, data):
    """
    Technique 2: RSI indicator (period 14).
    If RSI < 30 => Buy signal (oversold),
    If RSI > 70 => Sell signal (overbought).
    """
    period = 14
    delta = data["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    
    # Avoid division by zero; if avg_loss is 0, RSI is set to 100
    rs = avg_gain / avg_loss.replace(0, 1)
    rsi = 100 - (100 / (1 + rs))
    
    # Make sure we get a single float value
    try:
        last_rsi = float(rsi.iloc[-1].item())  # Using .item() to avoid FutureWarning
        if np.isnan(last_rsi):
            return None
        if last_rsi < 30:
            return "Buy"
        elif last_rsi > 70:
            return "Sell"
    except (IndexError, TypeError):
        return None
    
    return None


def technique_macd(stock, data):
    """
    Technique 3: MACD indicator.
    Determines if a bullish (Buy) or bearish (Sell) crossover has occurred in the last two days.
    """
    exp1 = data["Close"].ewm(span=12, adjust=False).mean()
    exp2 = data["Close"].ewm(span=26, adjust=False).mean()
    macd_line = exp1 - exp2
    signal_line = macd_line.ewm(span=9, adjust=False).mean()

    if len(macd_line) < 2 or len(signal_line) < 2:
        return None

    # Convert Series values to floats using .item()
    prev_macd = float(macd_line.iloc[-2].item())
    curr_macd = float(macd_line.iloc[-1].item())
    prev_signal = float(signal_line.iloc[-2].item())
    curr_signal = float(signal_line.iloc[-1].item())

    if prev_macd < prev_signal and curr_macd > curr_signal:
        return "Buy"
    elif prev_macd > prev_signal and curr_macd < curr_signal:
        return "Sell"
    else:
        return None

def technique_bollinger_bands(stock, data):
    """
    Technique 4: Bollinger Bands.
    Using a 20-day period, if the current price is below the lower band => Buy,
    if above the upper band => Sell.
    """
    period = 20
    if len(data) < period:
        return None

    sma = data["Close"].rolling(window=period).mean()
    std = data["Close"].rolling(window=period).std()
    upper_band = sma + 2 * std
    lower_band = sma - 2 * std

    # Convert Series values to floats using .item()
    current_price = float(data["Close"].iloc[-1].item())
    current_upper = float(upper_band.iloc[-1].item())
    current_lower = float(lower_band.iloc[-1].item())

    if current_price < current_lower:
        return "Buy"
    elif current_price > current_upper:
        return "Sell"
    else:
        return None

def technique_stochastic(stock, data):
    """
    Technique 5: Stochastic Oscillator.
    Calculates the %K value over a 14 day period.
    If %K < 20 => Buy signal (oversold),
    if %K > 80 => Sell signal (overbought).
    """
    period = 14
    if len(data) < period:
        return None

    low_min = data["Low"].rolling(window=period).min()
    high_max = data["High"].rolling(window=period).max()
    stochastic = 100 * (data["Close"] - low_min) / (high_max - low_min)
    
    try:
        last_val = float(stochastic.iloc[-1].item())
        if np.isnan(last_val):
            return None
        if last_val < 20:
            return "Buy"
        elif last_val > 80:
            return "Sell"
    except (IndexError, TypeError):
        return None
    
    return None

def technique_cci(stock, data):
    """
    Technique 6: Commodity Channel Index (CCI).
    Computes CCI with a 20-day period.
    If CCI < -100 => Buy signal,
    if CCI > 100 => Sell signal.
    """
    period = 20
    if len(data) < period:
        return None

    TP = (data["High"] + data["Low"] + data["Close"]) / 3
    sma_tp = TP.rolling(window=period).mean()
    # Compute mean absolute deviation
    mad = TP.rolling(window=period).apply(lambda x: np.mean(np.abs(x - np.mean(x))), raw=True)
    
    try:
        last_mad = float(mad.iloc[-1].item())
        if last_mad == 0:
            return None
            
        cci = (TP - sma_tp) / (0.015 * mad)
        last_cci = float(cci.iloc[-1].item())
        
        if np.isnan(last_cci):
            return None
        if last_cci < -100:
            return "Buy"
        elif last_cci > 100:
            return "Sell"
    except (IndexError, TypeError):
        return None
    
    return None

def generate_html_email(buy_list, sell_list, detailed_signals):
    """
    Builds a responsive, inline CSS HTML email body that includes:
      - Aggregated recommendations for likely buys and sells.
      - A detailed table showing, for each stock, the technique (and its signal) that yielded a recommendation.
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
        max-width: 600px;
        margin: auto;
        background-color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
      }}
      h1, h2 {{
        color: #333333;
      }}
      table {{
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 20px;
      }}
      th, td {{
        border: 1px solid #dddddd;
        padding: 8px;
        text-align: left;
      }}
      th {{
        background-color: #f2f2f2;
      }}
      .buy-signal {{
        background-color: #e6ffe6;  /* Soft green */
      }}
      .sell-signal {{
        background-color: #ffe6e6;  /* Soft red */
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
      <h1>Daily Stock Signals</h1>
      <h2>Aggregated Recommendations</h2>
      <table>
        <tr>
          <th>Likely Buys</th>
          <th>Likely Sells</th>
        </tr>
        <tr>
          <td class="buy-signal">{"<br>".join(buy_list) if buy_list else "None"}</td>
          <td class="sell-signal">{"<br>".join(sell_list) if sell_list else "None"}</td>
        </tr>
      </table>
      <h2>Signals by Technique</h2>
      <table>
        <tr>
          <th>Stock</th>
          <th>Technique</th>
          <th>Signal</th>
        </tr>
    """
    for stock, signals in detailed_signals.items():
        for technique, signal in signals:
            signal_class = "buy-signal" if signal == "Buy" else "sell-signal"
            html += f'<tr><td>{stock}</td><td>{technique}</td><td class="{signal_class}">{signal}</td></tr>'
    html += """\
      </table>
    </div>
  </body>
</html>
"""
    return html

def send_email(sender, receiver, smtp_server, smtp_port, login, password, html_body):
    """
    Composes and sends an HTML formatted email.
    """
    subject = "Daily Stock Signals"
    msg = MIMEMultipart("alternative")
    msg["From"] = sender
    msg["To"] = receiver
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html"))

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
    # Load stock symbols from stocks.txt
    try:
        with open("stocks.txt", "r") as f:
            stocks = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"Error reading stocks.txt: {e}")
        return

    aggregated_buys = []
    aggregated_sells = []
    detailed_signals = {}  # Format: {stock: [(technique, signal), ...]}

    # Process each stock by downloading its data and running each analysis technique.
    for stock in stocks:
        print(f"Analyzing {stock}...")
        data = get_stock_data(stock)
        if data is None:
            continue

        signals = []
        # Technique: Moving Average Cross-over (50/200 MA)
        ma_signal = technique_ma_crossover(stock, data)
        if ma_signal:
            signals.append(("50/200 MA Crossover", ma_signal))
        
        # Technique: RSI
        rsi_signal = technique_rsi(stock, data)
        if rsi_signal:
            signals.append(("RSI", rsi_signal))
        
        # Technique: MACD
        macd_signal = technique_macd(stock, data)
        if macd_signal:
            signals.append(("MACD", macd_signal))
        
        # Technique: Bollinger Bands
        bb_signal = technique_bollinger_bands(stock, data)
        if bb_signal:
            signals.append(("Bollinger Bands", bb_signal))
        
        # Technique: Stochastic Oscillator
        stochastic_signal = technique_stochastic(stock, data)
        if stochastic_signal:
            signals.append(("Stochastic Oscillator", stochastic_signal))
        
        # Technique: Commodity Channel Index (CCI)
        cci_signal = technique_cci(stock, data)
        if cci_signal:
            signals.append(("CCI", cci_signal))
        
        if signals:
            detailed_signals[stock] = signals

            # Aggregate signals: if more Buy signals than Sell then mark as a likely buy, and vice versa.
            buy_count = sum(1 for _, sig in signals if sig == "Buy")
            sell_count = sum(1 for _, sig in signals if sig == "Sell")
            if buy_count > sell_count:
                aggregated_buys.append(stock)
            elif sell_count > buy_count:
                aggregated_sells.append(stock)

    html_body = generate_html_email(aggregated_buys, aggregated_sells, detailed_signals)

    # Email settings (update/verify these in your .env file before running)
    sender = os.getenv("GOOGLE_ACCOUNT")
    receiver = os.getenv("GOOGLE_ACCOUNT")
    smtp_server = "smtp.gmail.com"  # For Gmail SMTP
    smtp_port = 587  # Use port 587 with TLS
    login = os.getenv("GOOGLE_ACCOUNT")
    app_password = os.getenv("GOOGLE_APP_PASSWORD")

    send_email(sender, receiver, smtp_server, smtp_port, login, app_password, html_body)


if __name__ == "__main__":
    main()
