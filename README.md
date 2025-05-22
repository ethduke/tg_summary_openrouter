# Telegram Easy Summary

A tool that creates AI-powered summaries of Telegram chat messages using OpenRouter AI models.

## Features

- Fetch messages from Telegram channels/chats
- Focus on specific users while maintaining conversation context
- Generate summaries using any model from OpenRouter (default: GPT-3.5 Turbo)
- Analyze messages by participant with individual summaries
- Fetch only unread messages with a single flag

## Setup

1. Clone this repository
2. Install dependencies: `pip install -r requirements.txt`
3. Configure `.env` file:
   ```
   TELEGRAM_API_ID=your_api_id
   TELEGRAM_API_HASH=your_api_hash
   TELEGRAM_STRING_SESSION=your_session_string
   DEFAULT_TELEGRAM_CHANNEL_ID=your_default_channel_id
   OPENROUTER_API_KEY=your_openrouter_api_key
   ```

## Usage

```bash
# Basic usage with default settings
python main.py

# Custom examples
python main.py -n 200                              # Fetch 200 messages
python main.py -c @channel_name                    # Specify channel
python main.py -u @username1 @username2            # Focus on users
python main.py -o summary.txt                      # Save to file
python main.py --unread                            # Only unread messages
python main.py --model anthropic/claude-3-5-sonnet  # Use Claude model from OpenRouter
python main.py --model openai/gpt-4o              # Use GPT-4o model from OpenRouter
```

### Command Options

- `-c`, `--chat_id`: Chat ID or username (default: from config)
- `-n`, `--limit`: Max messages to fetch (default: 100)
- `-u`, `--users`: Users to focus on
- `-o`, `--output`: Output file path
- `-m`, `--model`: OpenRouter model for summarization
- `--unread`: Fetch only unread messages

## Customizing Prompts

The tool uses separate markdown files for prompts located in `data/prompts/`:

- `example_prompt.md-example`: Main prompt for generating the overall conversation summary

To customize prompts:

1. Save as the relevant `.md` file in `data/prompts/`
2. Your changes will be automatically used when running the tool
3. Use template variables like `{participants}` and `{messages}` in your prompts
4. In your config.yaml file, set the `prompt_template_name` under `default_prompt` to match your preferred prompt file name (without the .md extension). For example, if you want to use summary_prompt.md, set it to 'summary_prompt'

## Configuration

Edit `config.yaml` to change default settings like message limits, default channel, and model selection.

### OpenRouter Models

The configuration includes these models that you can use:

1. `openai/o4-mini` - OpenAI's O4 Mini model
2. `anthropic/claude-3.7-sonnet` - Anthropic's Claude 3.7 Sonnet model
3. `google/gemini-2.5-flash-preview-05-20` - Google's Gemini 2.5 Flash Preview

### OpenRouter Credits

To use this tool, you need OpenRouter credits. To replenish your credits:

1. Visit https://openrouter.ai/settings/credits
2. Add more credits to your account using available payment methods

## License

MIT 