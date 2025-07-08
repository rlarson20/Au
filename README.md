# Au, the simple code editing agent

Au is a simple CLI code editing agent powered by OpenRouter's API.

## Installation and setup

1. Clone this repo:

```bash
git clone https://github.com/rlarson20/Au.git
```

2. create a `.env` file containing an OpenRouter API key in the repository.
3. `uv sync` to ensure the virtual environment is setup.
4. `uv run main.py` to start pair programming in the terminal.

## Tools

### Read File

Au can read the contents of a text file in a directory.

### List Files

Au can list the files inside a directory, defaulting to current working directory.

### Edit Files

Au can edit files by replacing a string with another string. This seems to work best with Anthropic's models, so we default to `claude-sonnet-4`.

## Conclusion

This was about a day's worth of effort building a proof of concept that I didn't hate and wasn't just from the documentation.
This isn't meant for production use, but if you like the minimalist chat-like look, go nuts, it should work fine.
