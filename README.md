# Web Automation Agent

An intelligent AI agent for web automation. Chat naturally with web pages, search the web with citations, and automate complex tasks through conversation.

## Features

- Conversational Interface - Chat naturally about web pages
- Research Mode - Search the web with citations and source attribution
- Smart Automation - Execute tasks through conversation
- Page Understanding - Deep analysis and content extraction
- Multi-turn Context - Remembers conversation history

## Quick Start

### Web UI (Recommended!)



```bash
# Terminal 1 - Start backend
python api_server.py

# Terminal 2 - Start frontend
cd frontend && npm run dev

# Open browser: http://localhost:3000
```

See [SETUP_GUIDE.md](SETUP_GUIDE.md) for complete instructions.

### CLI Chat Interface

```bash
# Interactive terminal chat
python chat_assistant.py --url "https://linear.app"

# Then chat naturally:
> What can I do on this page?
> Create a new project called "Q1 Goals"
> How does Linear compare to Asana?
```

### Original Automation

```bash
# One-shot task execution
python main.py --task "Create a project" --url "https://linear.app"
```

## Setup

1.  **Install Dependencies**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    playwright install chromium
    ```

2.  **Configure API Keys**:
    Copy `.env.example` to `.env` and add your API keys:
    ```bash
    cp .env.example .env
    # Edit .env and set:
    OPENAI_API_KEY=sk-...              # Required for all features
    TAVILY_API_KEY=tvly-...            # Optional: for web search in research mode
    ```

## Usage

### Interactive Chat Mode (Recommended)

```bash
# Start the chat assistant
python chat_assistant.py --url "https://linear.app"

# Available commands:
/mode assist      # Answer questions about pages
/mode research    # Search web with citations
/mode automate    # Execute tasks
/navigate <url>   # Go to new page
/actions          # Get smart suggestions
/help             # Show all commands
```

### Original Automation Mode

```bash
python main.py --task "Search for 'Artificial Intelligence' and click the first result" --url "https://en.wikipedia.org" --output "output/wiki_test"
```

## Documentation

- **[Setup Guide](SETUP_GUIDE.md)** - Complete installation guide
- **[Frontend Guide](FRONTEND_GUIDE.md)** - UI documentation
- **[Examples](EXAMPLES.md)** - Practical usage examples
- **[Architecture](ARCHITECTURE.md)** - Technical architecture details

## Output

The agent will create a directory (default: `output/run_X`) containing:
-   `step_N_TIMESTAMP.jpg`: Screenshots of each state.
-   `manifest.json`: A JSON file describing the workflow, including agent reasoning, actions taken, and metadata for each step.

## Architecture

### Core Components

-   `chat_assistant.py`: Interactive chat interface with multi-mode support
-   `src/perplexity_agent.py`: Conversational agent with memory and context
-   `src/web_researcher.py`: Web search, content extraction, and synthesis
-   `src/vision_agent.py`: Vision-based automation and decision making
-   `src/browser_manager.py`: Playwright browser control
-   `src/capturer.py`: Original automation workflow orchestrator

### Modes of Operation

1. **Assist Mode** - Answer questions about current page
2. **Research Mode** - Search web and synthesize with citations
3. **Automate Mode** - Execute tasks through conversation

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed technical documentation.
