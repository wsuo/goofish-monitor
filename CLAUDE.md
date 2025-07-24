# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI-powered Goofish (闲鱼) monitoring and analysis tool that uses web scraping with Playwright, AI analysis with OpenAI-compatible APIs, and provides a web interface for task management. The system monitors second-hand marketplace listings, analyzes them using multimodal AI models, and sends notifications for recommended items.

## Core Architecture

### Main Components
- `spider_v2.py`: Core web scraping engine using Playwright async
- `web_server.py`: FastAPI web server providing management interface
- `login.py`: Authentication and session management for Goofish
- `prompt_generator.py`: AI prompt generation and task creation utility
- `config.json`: Central configuration file defining all monitoring tasks

### Key Dependencies
- **Playwright**: Async web scraping and browser automation
- **FastAPI**: Web API server with Jinja2 templates
- **OpenAI**: AI analysis using multimodal models (requires vision support)
- **python-dotenv**: Environment configuration management

### Directory Structure
- `prompts/`: AI analysis criteria files (base_prompt.txt + task-specific _criteria.txt)
- `templates/`: Jinja2 HTML templates for web UI
- `static/`: CSS/JS assets for web interface
- `images/`: Auto-created directory for downloaded product images
- `logs/`: Auto-created directory for application logs
- `jsonl/`: Auto-created directory for analysis results

## Common Development Commands

### Environment Setup
```bash
pip install -r requirements.txt
```

### Initial Login (Required)
```bash
python login.py
```
This must be run first to generate `xianyu_state.json` session file via QR code scan.

### Run Core Spider
```bash
python spider_v2.py
# Debug mode (limit items per task):
python spider_v2.py --debug-limit 2
```

### Start Web Server
```bash
python web_server.py
# Access at: http://127.0.0.1:8000
```

### Create New Tasks via CLI
```bash
python prompt_generator.py \
  --description "购买需求描述" \
  --output prompts/task_criteria.txt \
  --task-name "任务名称" \
  --keyword "搜索关键词" \
  --min-price "最低价格" \
  --max-price "最高价格"
```

### Docker Deployment
```bash
# Note: login.py must be run on host first to generate xianyu_state.json
docker-compose up -d
docker-compose logs -f  # View logs
docker-compose down     # Stop and remove
```

## Configuration Management

### Environment Variables (.env)
Required variables:
- `OPENAI_API_KEY`: API key for AI model
- `OPENAI_BASE_URL`: OpenAI-compatible API endpoint 
- `OPENAI_MODEL_NAME`: Model name (must support vision/multimodal)
- `NTFY_TOPIC_URL`: Notification service URL
- `RUN_HEADLESS`: Browser headless mode (true/false)
- `SERVER_PORT`: Web server port (default: 8000)

Optional variables:
- `WX_BOT_URL`: WeChat bot webhook
- `PCURL_TO_MOBILE`: Convert PC URLs to mobile (true/false)
- `LOGIN_IS_EDGE`: Use Edge browser instead of Chrome

### Task Configuration (config.json)
Each task contains:
- `task_name`: Display name
- `enabled`: Active status
- `keyword`: Search term
- `max_pages`: Pages to scrape per run
- `personal_only`: Filter for individual sellers
- `min_price`/`max_price`: Price range filters
- `ai_prompt_base_file`: Base AI prompt file
- `ai_prompt_criteria_file`: Task-specific criteria file

## AI Analysis System

The system uses a two-file prompt structure:
1. `prompts/base_prompt.txt`: Common analysis framework
2. `prompts/{task}_criteria.txt`: Task-specific evaluation criteria

AI models must support vision/multimodal input for product image analysis. The system downloads product images and sends them along with product details to the AI for analysis.

## Web Interface Features

- **Task Management**: Create, edit, enable/disable monitoring tasks
- **AI Task Creation**: Generate tasks from natural language descriptions
- **Results Viewing**: Browse analyzed products with AI recommendations
- **Live Logs**: Real-time monitoring of scraping activities
- **System Status**: Check configuration and login status
- **Prompt Editing**: Online editing of AI analysis prompts

## Important Notes

### Session Management
- `xianyu_state.json` contains authentication cookies and must be generated via `login.py`
- Session may expire and require re-authentication
- For headless mode issues, set `RUN_HEADLESS=false` to handle captchas manually

### Anti-Detection Measures
- Built-in random delays and human-like behaviors
- Avoid running too many concurrent tasks
- Monitor for "异常流量" warnings from platform

### AI Model Requirements
- Must support multimodal/vision capabilities
- Examples: GPT-4o, Gemini-1.5-Pro, DeepSeek-V2, Qwen-VL-Plus
- Text-only models will fail or provide poor analysis quality

## Development Patterns

### Adding New Features
- Follow existing FastAPI patterns in `web_server.py`
- Use async/await for I/O operations
- Maintain separation between scraping logic and web interface

### Extending AI Analysis
- Modify prompts in `prompts/` directory rather than hardcoding
- Test prompt changes through web interface
- Ensure prompts work with multimodal input format

### Error Handling
- Check for common issues: network timeouts, captchas, session expiry
- Implement graceful degradation for AI API failures
- Log errors appropriately for debugging