import requests

def GetStockInfo(ticker):
    url = f"https://j.gravelle.us/APIs/Stocks/tickerApi.php?q={ticker}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data["status"] == "OK" and data["resultsCount"] > 0:
            result = data["results"][0]
            return f"Stock info for {ticker}:\nOpen: {result['o']}\nClose: {result['c']}\nHigh: {result['h']}\nLow: {result['l']}\nVolume: {result['v']}"
    return f"No stock info found for {ticker}"