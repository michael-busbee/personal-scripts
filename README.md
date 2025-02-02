# personal-scripts

## stock-watcher.py

This script is used to keep watch on a portfolio of stocks. It tracks the 200 and 50 day moving averages and alerts when their lines have crossed.

### Installation Instructions:

```

sudo apt install git
git clone https://github.com/michael-busbee/personal-scripts.git
cd personal-scripts/
sudo apt install python3-pip -y
sudo apt install python3-dotenv
pip install yfinance 
```

In the same directory as the stock-watcher.py script you will need to create a file called `stocks.txt` that contain **ONLY** the **STOCK SYMBOLS** (Not names) of interest, one per line.

You will also need to create a `.env` file in the same directory and set values for `GOOGLE_ACCOUNT=example@gmail.com` and `GOOGLE_APP_PASSWORD=[Generated App Password]` 

To run the script with just:

```
python3 stock-watcher.py
```

You can then background the process by pressing `CTRL+Z` then `bg`. To check the status of backgrounded processes use `jobs` 