# test_web_search.py
"""
Run this file to check that the Responses API + web search work end-to-end.

• Requires: python-openai ≥ 1.14.0, python-dotenv
• Make sure you have OPENAI_API_KEY in a .env file or in your shell.
"""

import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()                    # picks up OPENAI_API_KEY (and friends)
client = OpenAI()                # the key is read automatically


def main() -> None:
    query = "Search the web for today's headlines."

    response = client.responses.create(
        model="gpt-4o",
        input=query,
        tools=[
            {
                "type": "web_search_preview",
                # narrow results to the UK for consistency
                "user_location": {
                    "type": "approximate",
                    "country": "GB",
                    "city": "London",
                    "region": "London",
                },
                "search_context_size": "medium",   # ‘high’ or ‘low’ are also valid
            }
        ],
    )

    ####################################################################
    # The Responses API returns a list-like object:
    #   • one item with type="web_search_call"
    #   • one item with type="message" (the assistant’s reply)
    ####################################################################
    assistant_msg = next(
        (item for item in response if getattr(item, "type", None) == "message"),
        None,
    )
    if assistant_msg is None:
        raise RuntimeError("No assistant message found in response!")

    # 1️⃣  The plain-text answer
    print("\n=== Assistant output ===\n")
    print(assistant_msg.content[0].text)

    # 2️⃣  URL-citation metadata
    print("\n=== Citations ===\n")
    annotations = getattr(assistant_msg.content[0], "annotations", []) or []
    for ann in annotations:
        if ann.type == "url_citation":
            print(f"- {ann.title}\n  {ann.url}\n"
                  f"  (text indices {ann.start_index}–{ann.end_index})")

    # 3️⃣  If you’d like to see the raw JSON, uncomment the next line:
    # print(json.dumps(response.model_dump(), indent=2))


if __name__ == "__main__":
    main()
