import os
import json
import logging
import re
from openai import OpenAI
from dotenv import load_dotenv

# Load API Key
load_dotenv()
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Configure Logging
LOG_FILE = "strategy_errors.log"
DEBUG_FILE = "strategy_debug.json"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def sanitize_json_response(response_text):
    """Removes unwanted characters (e.g., Markdown formatting) from the JSON response."""
    # Remove Markdown code block markers (e.g., ```json ... ```)
    response_text = re.sub(r"```json\s*|\s*```", "", response_text).strip()
    return response_text

def convert_risk_management_values(strategy_json):
    """Ensures risk management values are numerical."""
    if "risk_management" in strategy_json:
        for key in ["stop_loss", "take_profit", "position_size"]:
            if key in strategy_json["risk_management"]:
                try:
                    strategy_json["risk_management"][key] = float(strategy_json["risk_management"][key])
                except ValueError:
                    raise ValueError(f"Invalid numeric value for {key}: {strategy_json['risk_management'][key]}")
    return strategy_json

def generate_trading_strategy(user_input, chat_history=None):
    """
    Generates a structured trading strategy JSON using ChatGPT based on user input.

    Parameters:
        user_input (str): The user's request for a trading strategy.
        chat_history (list, optional): Previous chat context for better responses.

    Returns:
        dict: A JSON dictionary containing the generated trading strategy.
    """
    print("📌 Debug: Starting strategy generation...")

    # System Prompt
    system_prompt = """You are an expert in algorithmic trading strategy generation. 
    Your goal is to produce structured JSON strategies based on user input, formatted correctly for execution in a trading system.

    🚀 **IMPORTANT**: Respond **ONLY** with a valid JSON object, **no additional text or markdown** before or after the JSON.

    ⚡ **Strategy JSON Format**:
    {
        "strategy_name": "<Descriptive strategy name>",
        "description": "<Brief explanation of the strategy>",
        "indicators": [
            {
                "type": "<Indicator Type>",
                "parameters": {"<Parameter Name>": <Value>},
                "condition": "<Condition>",
                "value": <Numeric Value> (if applicable),
                "reference": "<Reference Indicator>" (if applicable),
                "reference_parameters": {"<Parameter Name>": <Value>} (if applicable)
            }
        ],
        "entry_condition": "<'all' or 'any'>",
        "exit_condition": {
            "type": "<Indicator Type>",
            "parameters": {"<Parameter Name>": <Value>},
            "condition": "<Condition>",
            "value": <Numeric Value> (if applicable)
        },
        "risk_management": {
            "stop_loss": <Percentage or Value>,
            "take_profit": <Percentage or Value>,
            "position_size": <Portfolio Percentage or Fixed Amount>
        }
    }

    ⚡ **Available Indicators**:
    - RSI → {"period": 5 to 50, default 14}
    - MACD → {"fast_period": 5 to 15, "slow_period": 20 to 40, "signal_period": 5 to 15, default 12-26-9}
    - Moving Average → {"period": 10 to 200, "type": "SMA, EMA, WMA", default 50-SMA}
    - Bollinger Bands → {"period": 10 to 50, "std_dev": 1 to 3, default 20-2}
    - Volume → {"lookback_period": 5 to 50, default 10}
    - Stochastic Oscillator → {"k_period": 5 to 20, "d_period": 3 to 10, "smooth": 3 to 5, default 14-3-3}
    - Average True Range (ATR) → {"period": 5 to 50, default 14}
    - Parabolic SAR → {"step": 0.01 to 0.1, "max_step": 0.1 to 0.5, default 0.02-0.2}
    - ADX (Average Directional Index) → {"period": 5 to 50, default 14}
    - Ichimoku Cloud → {"tenkan": 5 to 20, "kijun": 20 to 40, "senkou": 40 to 100, default 9-26-52}
    - SuperTrend → {"atr_period": 5 to 20, "multiplier": 1 to 5, default 10-3}
    - Fibonacci Retracement → {"levels": 0.236 to 0.786, default [0.236, 0.382, 0.5, 0.618, 0.786]}
    - Pivot Points → {"method": "standard, fibonacci, camarilla", default standard}
    - On-Balance Volume (OBV) → {"lookback_period": 5 to 50, default 10}
    - Chaikin Money Flow (CMF) → {"period": 10 to 50, default 20}
    - Accumulation/Distribution Line (A/D Line) → {"lookback_period": 5 to 50, default 10}
    - VWAP (Volume Weighted Average Price) → {"intraday": true, default true}
    - Williams %R → {"period": 5 to 50, default 14}
    - Momentum Indicator (MOM) → {"period": 5 to 50, default 10}
    - Rate of Change (ROC) → {"period": 5 to 50, default 10}
    - Awesome Oscillator (AO) → {"short_period": 3 to 10, "long_period": 20 to 50, default 5-34}
    - Keltner Channels → {"period": 10 to 50, "multiplier": 1 to 3, default 20-2}
    - Donchian Channels → {"lookback_period": 10 to 50, default 20}
    - Chaikin Volatility Indicator → {"period": 5 to 50, default 10}
    - Z-Score Indicator → {"lookback_period": 10 to 50, default 20}
    - Fractal Indicator → {"lookback_period": 3 to 10, default 5}

    ⚡ **Conditions**:
    - <, >, <=, >=
    - "crosses_above", "crosses_below"
    - "within_range", "outside_range"
    - "equal", "not_equal"
    - "increasing", "decreasing"
    - "highest_in_period", "lowest_in_period"
    - "above_moving_average", "below_moving_average"
    - "touches_upper_band", "touches_lower_band"
    - "breaks_above_resistance", "breaks_below_support"
    - "divergence_bullish", "divergence_bearish"

    ⚡ **Entry & Exit Conditions**:
    - `"all"` → All indicators must be met (AND logic).
    - `"any"` → At least one indicator must be met (OR logic).

    ⚡ **Risk Management Options**:
    - `stop_loss`: `"2.0"` (Percentage-based or fixed value)
    - `take_profit`: `"5.0"`
    - `position_size`: `"0.05"` (Portfolio percentage or fixed amount)

    **DO NOT** include explanations, formatting, or markdown in your response—only return the raw JSON object.
    """

    # Prepare messages for ChatGPT
    messages = [{"role": "system", "content": system_prompt}]

    # If chat history exists, include it
    if chat_history and isinstance(chat_history, list):
        messages.extend(chat_history)

    # Add user's latest request
    messages.append({"role": "user", "content": user_input})

    print("📌 Debug: Sending request to OpenAI API using `gpt-4o-mini`...")

    # Call OpenAI API using the latest client syntax
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Using gpt-4o-mini as requested
            messages=messages
        )

        # Extract API response content
        strategy_json = response.choices[0].message.content.strip()

        print(f"📌 Debug: Raw API Response:\n{strategy_json}")

        # Save raw response to a debug file
        with open(DEBUG_FILE, "w", encoding="utf-8") as debug_file:
            debug_file.write(strategy_json)

        # Sanitize and parse JSON
        strategy_json = sanitize_json_response(strategy_json)
        parsed_json = json.loads(strategy_json)

        # Convert numeric values in risk management
        parsed_json = convert_risk_management_values(parsed_json)

        print("✅ Debug: Successfully parsed and validated JSON strategy.")
        return parsed_json

    except json.JSONDecodeError:
        error_message = "Invalid JSON format generated by ChatGPT."
        logging.error(error_message)
        print(f"❌ Debug: {error_message}")
        return {"error": error_message}

    except ValueError as e:
        error_message = f"Validation Error: {str(e)}"
        logging.error(error_message)
        print(f"❌ Debug: {error_message}")
        return {"error": error_message}

    except Exception as e:
        error_message = f"API request failed: {str(e)}"
        logging.error(error_message)
        print(f"❌ Debug: {error_message}")
        return {"error": error_message}
