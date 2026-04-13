import os
from anthropic import Anthropic

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

response = client.completions.create(
    model="claude-3.5-code",  # or whatever current Claude Code model is available
    prompt="Summarize this code...",
    max_tokens_to_sample=200,
)

print(response.completion)