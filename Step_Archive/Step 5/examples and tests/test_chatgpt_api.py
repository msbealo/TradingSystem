# test_chatgpt_api.py

from chatgpt_api import ChatGPTAPI

def test_chatgpt_api():
    """
    Tests both the trading strategy generation and stock screener generation
    capabilities of the ChatGPTAPI class.
    """
    print("🔄 Starting ChatGPTAPI test...")

    # 1) Instantiate the API class
    api = ChatGPTAPI(model_name="gpt-4o-mini")  # or whatever model you use

    # 2) Generate a trading strategy
    strategy_prompt = "Create a simple moving average crossover strategy using two moving averages."
    strategy_response = api.generate_trading_strategy(strategy_prompt)

    print("\n📌 Trading Strategy Test")
    if "error" in strategy_response:
        print(f"❌ Error in generating strategy: {strategy_response['error']}")
    else:
        print("✅ Successfully generated trading strategy JSON:")
        print(strategy_response)  # show the full JSON

    # 3) Generate a stock screener
    screener_prompt = "Find tech stocks with a P/E ratio under 20, revenue growth over 5%, and dividend yield above 3%."
    screener_response = api.generate_stock_screener(screener_prompt)

    print("\n📌 Stock Screener Test")
    if "error" in screener_response:
        print(f"❌ Error in generating stock screener: {screener_response['error']}")
    else:
        print("✅ Successfully generated stock screener JSON:")
        print(screener_response)
        # e.g. might be: { "criteria": { "sector": "Technology", "pe_ratio": {"max": 20}, ... } }

    print("\n🎉 All tests completed.")

if __name__ == "__main__":
    test_chatgpt_api()
