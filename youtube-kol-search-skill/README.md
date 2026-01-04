# How to Use the YouTube KOL Search Skill

This README explains how to use the YouTube KOL Search System skill with Claude.

## What is This Skill?

This skill enables Claude to help you build and deploy a complete YouTube KOL (Key Opinion Leader) discovery and analysis system. The system:

- Searches YouTube for channels by keywords
- Analyzes channel metrics and engagement
- Uses AI to evaluate channel-product fit
- Exports results to Excel
- Runs as a web application on your server/NAS

## Prerequisites

Before using this skill, you need:

1. **Docker & Docker Compose** installed on your system
2. **YouTube Data API v3 keys** (minimum 2 recommended) - [Get them here](https://console.cloud.google.com/apis/credentials)
3. **AI API key** - Either:
   - Deepseek API key - [Get it here](https://platform.deepseek.com/)
   - Zhipu AI key - [Get it here](https://open.bigmodel.cn/)
4. **Server/NAS** with at least 4GB RAM and 10GB disk space

## How to Use This Skill

### Step 1: Tell Claude You Want to Build the System

Simply ask Claude something like:

```
"I want to build a YouTube KOL search system to find channels 
for marketing my Windows optimization software. Can you help me 
set it up using the youtube-kol-search skill?"
```

Claude will automatically:
1. Read the SKILL.md to understand what to build
2. Access reference documentation for detailed implementation
3. Use scripts and assets to help you deploy

### Step 2: Claude Will Guide You Through Deployment

Claude will help you:

1. **Deploy the System**:
   ```bash
   # Claude will provide commands like:
   chmod +x scripts/deploy.sh
   ./scripts/deploy.sh
   ```

2. **Configure Environment**:
   - Edit `.env` file with your settings
   - Add API keys
   - Configure product information

3. **Test APIs**:
   ```bash
   python3 scripts/test_apis.py \
     --youtube-key YOUR_KEY \
     --ai-provider deepseek \
     --ai-key YOUR_AI_KEY
   ```

4. **Initialize Database**:
   ```bash
   python3 scripts/init_database.py \
     --password YOUR_DB_PASSWORD
   ```

### Step 3: Use the System

Once deployed, access:
- **Web Interface**: http://your-server:7853
- **API Documentation**: http://your-server:7854/docs

## What Claude Can Help With

### Building Components

Ask Claude to:
- "Build the YouTube API manager with key rotation"
- "Create the language detection module"
- "Implement the AI analysis service"
- "Build the Excel export functionality"
- "Create the Vue.js frontend"

### Troubleshooting

Ask Claude:
- "The API quota is being exhausted too quickly, how can I optimize?"
- "I'm getting rate limited, what should I change?"
- "How do I add more API keys?"
- "The AI analysis is too slow, can we make it faster?"

### Customization

Ask Claude:
- "Can you modify the AI prompt to focus more on subscriber count?"
- "Add a filter to only show channels with >100k subscribers"
- "Export data in a different Excel format"
- "Add support for another AI provider"

## Skill Structure

The skill contains:

```
youtube-kol-search-skill/
├── SKILL.md                    # Core documentation (Claude reads this)
├── references/                 # Detailed references
│   ├── architecture.md        # System architecture
│   ├── database_schema.md     # Database design
│   └── anti_ban_strategy.md   # Protection mechanisms
├── scripts/                    # Utility scripts
│   ├── init_database.py       # Database setup
│   ├── test_apis.py           # API testing
│   └── deploy.sh              # Deployment
└── assets/                     # Configuration templates
    ├── docker-compose.yml     # Docker configuration
    └── .env.example           # Environment template
```

## Example Conversation Flow

**You**: "I need to search YouTube for channels about PC optimization to promote my software"

**Claude**: "I'll help you build a YouTube KOL search system. Let me start by deploying the infrastructure..."
[Claude uses the skill to guide deployment]

**You**: "The search is working but AI analysis is slow"

**Claude**: "Let me optimize the AI analysis module. I'll enable concurrent processing..."
[Claude modifies code based on skill knowledge]

**You**: "Can you add a feature to export only channels with high relevance scores?"

**Claude**: "Sure, I'll add that filter to the export service..."
[Claude implements using architecture knowledge from references]

## Tips for Best Results

1. **Be Specific**: Tell Claude exactly what you want to build or modify
2. **Mention the Skill**: Say "using the youtube-kol-search skill" to ensure Claude loads it
3. **Ask for Explanations**: Claude can explain any part of the architecture
4. **Iterate**: Start with basic deployment, then ask for enhancements
5. **Share Errors**: If something fails, show Claude the error message

## Common Questions

**Q: Do I need to understand the code?**
A: No, Claude will handle the implementation. Just describe what you want.

**Q: Can I modify the system after Claude builds it?**
A: Yes! Ask Claude to make changes or explain code so you can modify it.

**Q: What if I don't have all the API keys yet?**
A: Claude can still build the system. You can add keys later via the web interface.

**Q: Can this work on platforms other than Synology NAS?**
A: Yes! Works on any system with Docker (Linux, Windows, macOS).

## Getting Help

If you're stuck:

1. **Ask Claude**: "I'm having trouble with [specific issue], can you help?"
2. **Check Logs**: `docker-compose logs -f` and share errors with Claude
3. **Review References**: Ask Claude to explain specific documentation
4. **Test Components**: Use `test_apis.py` to verify API connectivity

## What Makes This Skill Powerful

This skill gives Claude:
- **Complete Architecture Knowledge**: Every component and how they interact
- **Best Practices**: Proven patterns for YouTube API usage and AI integration
- **Protection Mechanisms**: 5-layer anti-ban strategy
- **Deployment Automation**: Scripts to deploy in minutes
- **Reference Documentation**: Deep technical details when needed

Claude uses this knowledge to build a production-ready system tailored to your needs.

## Next Steps

Ready to start? Just tell Claude:

```
"Let's build a YouTube KOL search system using the youtube-kol-search skill. 
I want to find channels for promoting [YOUR PRODUCT]."
```

Claude will take it from there! 🚀
