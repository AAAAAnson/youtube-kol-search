---
name: youtube-kol-search
description: A comprehensive YouTube KOL discovery and analysis system for product marketing. Use this skill when users need to (1) Search and discover YouTube channels (KOLs) by keywords, (2) Analyze channel metrics (subscribers, views, engagement rates), (3) Detect channel language and video content language, (4) Use AI (Deepseek/Zhipu) to evaluate channel-product fit for marketing campaigns, (5) Export analysis results to Excel with multiple sheets, (6) Deploy a Docker-based web system with real-time progress tracking on Synology NAS or other servers, (7) Manage YouTube API keys with automatic rotation and quota tracking, (8) Support incremental updates to track new channels over time.
---

# YouTube KOL Search System

A production-ready system for discovering, analyzing, and evaluating YouTube Key Opinion Leaders (KOLs) for product marketing campaigns.

## Overview

This system automates the entire KOL discovery workflow:

1. **Search**: Find YouTube channels by keywords with complete pagination
2. **Collect**: Gather channel metrics, subscriber counts, and recent video statistics
3. **Analyze**: Detect content language and use AI to evaluate channel-product alignment
4. **Export**: Generate comprehensive Excel reports with sortable/filterable data
5. **Monitor**: Track progress in real-time via WebSocket updates

## Quick Start

### Prerequisites

- Docker & Docker Compose installed
- YouTube Data API v3 keys (minimum 2 recommended)
- AI API key (Deepseek or Zhipu AI)
- Target: Synology NAS at `/volume2/web/youtube-kol-search` or any Docker host

### Deployment Steps

1. **Initialize the project structure**:
   ```bash
   # Run initialization script
   python scripts/init_database.py
   ```

2. **Configure environment variables**:
   ```bash
   # Copy template and edit
   cp assets/.env.example .env
   
   # Add your API keys
   nano .env
   ```

3. **Deploy with Docker**:
   ```bash
   # Deploy all services
   docker-compose up -d
   
   # Check status
   docker-compose ps
   ```

4. **Access the system**:
   - Frontend: http://192.168.31.199:7853
   - API Docs: http://192.168.31.199:7854/docs
   - MySQL: 192.168.31.199:7855
   - Redis: 192.168.31.199:7856

### First Search

1. Navigate to the web interface
2. Configure your product information (auto-scraped from website or manual entry)
3. Add YouTube API keys in Settings → API Management
4. Add AI API key (Deepseek or Zhipu)
5. Enter search keyword (e.g., "PC cleanup", "Windows optimization")
6. Choose mode: Normal (safe) or Accelerated (faster, higher API usage)
7. Monitor real-time progress as the system:
   - Searches all channels matching the keyword
   - Collects channel details and video statistics
   - Analyzes content with AI
   - Displays results progressively

## Core Workflow

### 1. Search Strategy

**Dual search approach** for comprehensive coverage:

```
Keyword Input → Two-phase search:
├─ Phase 1: Search type="channel" 
│  └─ Directly find channels
└─ Phase 2: Search type="video"
   └─ Extract unique channel IDs from videos
   
Result: Merged & deduplicated channel list
```

**Complete pagination**:
- Uses `nextPageToken` to fetch all results
- No result limit (fetches 100s or 1000s of channels)
- Automatic API key rotation when quota exhausted

### 2. Data Collection

For each discovered channel:

```python
Channel Basic Info:
├─ Channel ID, Name, URL
├─ Subscriber count
├─ Channel description
└─ Custom URL, thumbnail

Video Statistics (recent 10 videos):
├─ Average view count
├─ Average likes
├─ Average comments  
├─ Engagement rate = (likes + comments) / views
├─ Outlier detection (1.5×IQR rule)
└─ Language distribution per video
```

**Language Detection** (Method B - Comprehensive):
- Analyze channel description
- Analyze recent 10 video titles + descriptions
- Statistical voting for primary language
- Confidence score based on agreement

### 3. AI Analysis

**Single-threaded queue** to handle AI API limitations:

```
Channel data → Queue → AI Analyzer (Deepseek/Zhipu)
                          ├─ Relevance score (0-100)
                          ├─ Audience match analysis
                          ├─ Content alignment
                          ├─ Marketing recommendation
                          ├─ Key strengths
                          └─ Potential concerns
```

**Offline analysis support**:
- If AI API unavailable during search, skip analysis
- Data saved to database
- "Batch Analyze" button appears for unanalyzed channels
- Auto-retry mechanism (hourly) for failed analyses

### 4. Results & Export

**Web Interface Features**:
- Multi-column sorting (subscribers, engagement, AI score)
- Filters by language, subscriber range, score threshold
- "[NEW]" tags for incremental search results
- Real-time AI analysis status indicators
- Batch operations (select multiple for export/re-analysis)

**Excel Export** (3 sheets):
1. **Channel Overview**: All metrics in sortable table
2. **Video Details**: Individual video data per channel
3. **AI Analysis**: Full AI evaluation details

## Key Features

### Incremental Updates

When re-searching the same keyword:
- System detects previous search
- Prompts: "Incremental update (new channels only) or Full re-search?"
- New channels tagged with "[NEW]" badge
- Old channels marked as "disappeared" if no longer found
- Preserves historical data with status tracking

### API Management

**YouTube API**:
- Multi-key rotation with automatic quota tracking
- Daily quota: 10,000 units per key, auto-resets at UTC midnight
- Real-time quota dashboard showing usage per key
- Alert when quota < 1,000 units remaining

**AI API**:
- Choose Deepseek or Zhipu (single active provider)
- Test connection button with status indicator
- Fallback to offline mode if unavailable
- Frontend configuration (no code changes needed)

### Anti-Ban Protection

**5-layer protection strategy**:

1. **API Key Rotation**: Switch on quota exhaustion
2. **Request Throttling**: 
   - Normal mode: 0.5-1s delay between requests
   - Accelerated: 0.2-0.3s delay
3. **Rate Limiting**: Max 60 req/min normal, 100 accelerated
4. **Error Handling**: 
   - HTTP 429 → switch key immediately
   - HTTP 403 → pause key for 1 hour
5. **Exponential Backoff**: On repeated failures (2s, 4s, 8s, ...)

See `references/anti_ban_strategy.md` for detailed implementation.

### Caching Strategy

**Three-tier cache** for optimal performance:

```yaml
Channel Basic Info: Permanent (Redis + MySQL)
Video Statistics: 24 hours (Redis cache)
AI Analysis: Permanent (MySQL only)
```

Cache invalidation:
- Manual refresh button per channel
- Automatic refresh on "Full re-search"
- Configurable TTL in settings

## Configuration

### Product Information

**Auto-scrape mode** (recommended):
```json
{
  "product_url": "https://www.wmastercleanup.com/",
  "auto_scrape": true,
  "refresh_interval": "7 days"
}
```

System extracts:
- Product name
- Core features
- Target audience
- Key benefits
- Use cases

**Manual override**: Edit in Settings → Product Config

### Accelerated Mode

Toggle between safe and fast modes:

```yaml
Normal Mode:
  parallel_collectors: 1
  ai_concurrent: 1
  request_delay: 1.0s
  
Accelerated Mode:
  parallel_collectors: 5
  ai_concurrent: 3
  request_delay: 0.2s
  risk_warning: "May increase rate limiting risk"
```

## Architecture

The system uses a microservices architecture:

```
Frontend (Vue 3) → FastAPI Backend → Services Layer → Data Layer
                                      ├─ YouTube Collector
                                      ├─ Language Detector  
                                      ├─ AI Analyzer
                                      └─ Export Generator
                                                ↓
                                      ┌──────────────────┐
                                      │  MySQL (persist) │
                                      │  Redis (cache)   │
                                      └──────────────────┘
```

For detailed architecture, see `references/architecture.md`.

## Advanced Usage

### Custom AI Prompts

Modify AI analysis behavior in Settings → AI Configuration:

```python
# Default prompt template
prompt = f"""
Analyze this YouTube channel for {product_name}:

Channel: {channel_info}
Recent Videos: {video_data}

Evaluate:
1. Content relevance (0-100)
2. Audience match
3. Marketing potential
"""
```

### Batch Operations

**Scenario**: 500 channels found, want to re-analyze top 50 by subscribers

1. Sort by subscribers (descending)
2. Select top 50 channels
3. Click "Batch Re-analyze"
4. Monitor progress in real-time
5. Export updated results

### Database Queries

Direct MySQL access for custom analysis:

```sql
-- Find English tech channels with >100k subs
SELECT c.channel_title, c.subscriber_count, a.relevance_score
FROM channels c
JOIN ai_analysis a ON c.channel_id = a.channel_id
WHERE c.detected_language = 'en'
  AND c.subscriber_count > 100000
  AND a.relevance_score > 70
ORDER BY a.relevance_score DESC;
```

## Troubleshooting

**API quota exhausted on all keys**:
- System automatically pauses until UTC midnight
- Add more API keys in Settings
- Use cached data for already-searched keywords

**AI analysis stuck**:
- Check AI API status in Settings
- Verify API key validity with "Test Connection"
- Enable offline mode, analyze later when API recovers

**Channels missing from results**:
- Check if channels are private/deleted
- Verify keyword spelling
- Try broader search terms

**Deployment issues on Synology**:
- Ensure Docker package installed
- Check port availability (7853-7856)
- Verify `/volume2/web` write permissions

## References

For detailed information, consult these reference documents:

- **Architecture**: `references/architecture.md` - Complete system design, database schemas, API flows
- **API Integration**: `references/api_integration.md` - YouTube API & AI API implementation details
- **Database Schema**: `references/database_schema.md` - Full table definitions with indexes and relationships
- **Deployment Guide**: `references/deployment.md` - Step-by-step deployment on various platforms
- **Anti-Ban Strategy**: `references/anti_ban_strategy.md` - Detailed protection mechanisms

## Scripts

Utility scripts in `scripts/` directory:

- `init_database.py` - Initialize MySQL schema and seed data
- `test_apis.py` - Validate YouTube and AI API connectivity
- `deploy.sh` - One-command deployment automation
- `backup_data.py` - Backup search results and configurations

## Assets

Template files in `assets/` directory:

- `docker-compose.yml` - Container orchestration config
- `.env.example` - Environment variables template
- `nginx.conf` - Reverse proxy configuration
- `product_config.json` - Product information template

## Best Practices

1. **Start with 2-3 YouTube API keys** for rotation
2. **Use Normal mode first** to understand rate limits
3. **Enable auto-scrape** for product info to stay updated
4. **Review AI analysis** of 5-10 channels to validate relevance before trusting scores
5. **Export frequently** - Excel files serve as backups
6. **Monitor quota dashboard** during large searches
7. **Use incremental updates** for recurring searches to save quota

## Support

For issues or feature requests:
1. Check `references/troubleshooting.md`
2. Review Docker logs: `docker-compose logs -f`
3. Verify API keys in Settings dashboard

---

**System Requirements**: Docker 20+, 4GB RAM, 10GB disk space
**Tested On**: Synology DSM 7.0+, Ubuntu 20.04+, macOS 12+
**License**: Internal use only
