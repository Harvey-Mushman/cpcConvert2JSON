import anthropic
import base64
from pathlib import Path

api_key = Path("anthropicKey.txt").read_text().strip()
client = anthropic.Anthropic(api_key=api_key)

pdf_folder = Path("./certificates")
output_folder = Path("./json_output")
output_folder.mkdir(exist_ok=True)

for pdf_file in pdf_folder.glob("*.pdf"):
    with open(pdf_file, "rb") as f:
        pdf_base64 = base64.b64encode(f.read()).decode()

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=32000,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": pdf_base64
                    }
                },
                {
                    "type": "text",
                    "text": "Extract ALL data from this certificate into structured JSON. You MUST include every single commodity entry row from every page - do not skip, summarize, truncate, or add notes. Output only raw JSON with no commentary."
                }
            ]
        }]
    )

    # Save JSON
    output_file = output_folder / f"{pdf_file.stem}.json"
    with open(output_file, "w") as f:
        f.write(message.content[0].text)

    if message.stop_reason == "max_tokens":
        print(f"WARNING: {pdf_file.name} was TRUNCATED - output hit the token limit, data is incomplete!")
    else:
        print(f"Processed: {pdf_file.name} (complete)")
