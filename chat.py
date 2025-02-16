import os
import openai

def generate_strategy(prompt: str) -> str:
    # Load your API key from the environment variable
    openai.api_key = os.getenv("OPENAI_API_KEY")

    # print API key to verify it is loaded
    print(openai.api_key)

    # Create a chat completion using the new interface
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a trading strategy generator ..."},
            {"role": "user", "content": prompt}
        ]
    )

    # Return the assistant’s generated text
    return response.choices[0].message.content

import json

strategy_text = generate_strategy("Create a momentum strategy using RSI and MACD.")
print(strategy_text)
try:
    strategy_json = json.loads(strategy_text)
    print(strategy_json)
except json.JSONDecodeError:
    # Handle the case where ChatGPT returned text that's not valid JSON
    pass

