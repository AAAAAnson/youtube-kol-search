# System Architecture

## Overview

The YouTube KOL Search System is built with a modern microservices architecture optimized for scalability, maintainability, and performance.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Client Layer (Browser)                    │
│  ┌────────────┬────────────┬────────────┬────────────────┐  │
│  │ Search UI  │ Results    │ Settings   │ Real-time      │  │
│  │            │ Dashboard  │ Panel      │ Progress       │  │
│  └────────────┴────────────┴────────────┴────────────────┘  │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTP/WebSocket
┌────────────────────────────┴────────────────────────────────┐
│                     API Gateway (Nginx)                      │
│              Reverse Proxy + Load Balancing                  │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────┴────────────────────────────────┐
│                   Application Layer (FastAPI)                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  REST API Endpoints                                  │   │
│  │  ├─ POST /api/search/start                          │   │
│  │  ├─ GET  /api/search/{task_id}/status               │   │
│  │  ├─ GET  /api/channels                              │   │
│  │  ├─ POST /api/analyze/batch                         │   │
│  │  └─ GET  /api/export/excel                          │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  WebSocket Endpoints                                 │   │
│  │  └─ WS /ws/progress/{task_id}                       │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────┴────────────────────────────────┐
│                     Service Layer                            │
│  ┌──────────────┬──────────────┬──────────────┬──────────┐  │
│  │ Search       │ Collection   │ AI Analysis  │ Export   │  │
│  │ Orchestrator │ Service      │ Service      │ Service  │  │
│  └──────────────┴──────────────┴──────────────┴──────────┘  │
│  ┌──────────────┬──────────────┬──────────────┬──────────┐  │
│  │ YouTube API  │ Language     │ Cache        │ API Key  │  │
│  │ Manager      │ Detector     │ Manager      │ Manager  │  │
│  └──────────────┴──────────────┴──────────────┴──────────┘  │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────┴────────────────────────────────┐
│                      Data Layer                              │
│  ┌──────────────────┬─────────────────┬──────────────────┐  │
│  │  MySQL 8.0       │  Redis 7.0      │  Celery Queue    │  │
│  │  - Persistent    │  - Cache        │  - Async Tasks   │  │
│  │  - Relational    │  - Sessions     │  - AI Analysis   │  │
│  │  - ACID          │  - Rate Limit   │  - Background    │  │
│  └──────────────────┴─────────────────┴──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Frontend Layer (Vue 3 + Element Plus)

**Technology Stack**:
- Vue 3 (Composition API)
- Element Plus (UI components)
- Axios (HTTP client)
- Socket.IO Client (WebSocket)
- XLSX (Excel export)

**Key Components**:

```javascript
src/
├── views/
│   ├── SearchPage.vue          // Main search interface
│   ├── ResultsPage.vue          // Channel results table
│   ├── SettingsPage.vue         // Configuration panel
│   └── HistoryPage.vue          // Search history
├── components/
│   ├── ProgressMonitor.vue      // Real-time progress
│   ├── ChannelCard.vue          // Channel detail card
│   ├── APIKeyManager.vue        // API key CRUD
│   ├── FilterPanel.vue          // Result filters
│   └── ExportDialog.vue         // Export options
├── services/
│   ├── api.js                   // API client
│   ├── websocket.js             // WebSocket manager
│   └── excel.js                 // Excel generator
└── store/
    ├── search.js                // Search state
    ├── settings.js              // App settings
    └── channels.js              // Channel data
```

**State Management**:
- Pinia for reactive state
- Persistent storage for settings
- WebSocket state synchronization

### 2. API Gateway (Nginx)

**Configuration** (`nginx.conf`):

```nginx
upstream api_backend {
    server api:8000;
}

server {
    listen 7853;
    
    # Frontend static files
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }
    
    # API proxy
    location /api/ {
        proxy_pass http://api_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    # WebSocket upgrade
    location /ws/ {
        proxy_pass http://api_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### 3. Application Layer (FastAPI)

**Project Structure**:

```python
backend/
├── main.py                      # FastAPI app entry
├── api/
│   ├── routes/
│   │   ├── search.py            # Search endpoints
│   │   ├── channels.py          # Channel CRUD
│   │   ├── analysis.py          # AI analysis
│   │   └── settings.py          # Configuration
│   └── websocket/
│       └── progress.py          # Progress updates
├── services/
│   ├── search_orchestrator.py   # Main search logic
│   ├── youtube_collector.py     # YouTube data collection
│   ├── ai_analyzer.py           # AI analysis
│   ├── language_detector.py     # Language detection
│   ├── cache_manager.py         # Redis cache
│   └── export_service.py        # Excel export
├── core/
│   ├── youtube_api.py           # YouTube API manager
│   ├── api_key_manager.py       # API key rotation
│   ├── rate_limiter.py          # Rate limiting
│   └── config.py                # App configuration
├── models/
│   ├── database.py              # SQLAlchemy models
│   └── schemas.py               # Pydantic schemas
└── utils/
    ├── outlier_detection.py     # Statistical analysis
    └── helpers.py               # Utility functions
```

**Key Endpoints**:

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/search/start` | Start new search task |
| GET | `/api/search/{task_id}` | Get task status |
| GET | `/api/channels` | List channels with filters |
| POST | `/api/channels/{id}/analyze` | Re-analyze channel |
| POST | `/api/analyze/batch` | Batch AI analysis |
| GET | `/api/export/excel` | Generate Excel report |
| GET | `/api/settings/api-keys` | List API keys |
| POST | `/api/settings/api-keys` | Add API key |
| GET | `/api/settings/product` | Get product config |
| PUT | `/api/settings/product` | Update product config |

### 4. Service Layer

#### Search Orchestrator

**Workflow**:

```python
class SearchOrchestrator:
    async def execute_search(self, keyword: str, task_id: str):
        """Main search orchestration"""
        
        # Phase 1: Search
        channel_ids = await self._search_phase(keyword, task_id)
        # - Search type=channel
        # - Search type=video, extract channels
        # - Merge and deduplicate
        
        # Phase 2: Collection
        channels_data = await self._collection_phase(channel_ids, task_id)
        # - Batch fetch channel info
        # - Collect video statistics
        # - Detect languages
        # - Check cache first
        
        # Phase 3: AI Analysis
        analysis_results = await self._analysis_phase(channels_data, task_id)
        # - Queue channels for AI
        # - Single-threaded processing
        # - Handle failures gracefully
        
        # Phase 4: Finalize
        await self._finalize(task_id)
        # - Mark task complete
        # - Send completion event
        # - Generate summary
```

#### YouTube API Manager

**API Key Rotation Logic**:

```python
class YouTubeAPIManager:
    def get_available_key(self) -> str:
        """Get next available API key with quota"""
        
        # 1. Check all keys
        keys = self.db.query(APIKey).filter(
            APIKey.is_active == True
        ).order_by(APIKey.used_quota.asc()).all()
        
        # 2. Reset if new day
        for key in keys:
            if key.last_reset_date < today:
                key.used_quota = 0
                key.last_reset_date = today
        
        # 3. Find key with available quota
        for key in keys:
            if key.used_quota < key.daily_quota:
                return key.api_key
        
        # 4. All exhausted
        raise QuotaExhaustedException()
    
    def record_usage(self, api_key: str, units: int):
        """Track API usage"""
        self.db.query(APIKey).filter(
            APIKey.api_key == api_key
        ).update({
            "used_quota": APIKey.used_quota + units
        })
```

#### Language Detector (Method B)

**Comprehensive Detection**:

```python
class LanguageDetector:
    def detect_channel_language(self, channel: dict) -> dict:
        """Comprehensive language detection"""
        
        # 1. Detect channel description
        desc_lang = detect(channel['description'][:500])
        
        # 2. Detect video titles/descriptions
        video_langs = []
        for video in channel['recent_videos']:
            text = video['title'] + ' ' + video['description'][:200]
            video_langs.append(detect(text))
        
        # 3. Statistical voting
        lang_counts = Counter(video_langs)
        most_common_lang, count = lang_counts.most_common(1)[0]
        
        # 4. Calculate confidence
        confidence = count / len(video_langs)
        
        # 5. Cross-check with description
        if desc_lang == most_common_lang:
            confidence = min(confidence + 0.2, 1.0)
        
        return {
            'language': most_common_lang,
            'confidence': confidence,
            'distribution': dict(lang_counts)
        }
```

#### AI Analyzer

**Single-threaded Queue**:

```python
class AIAnalyzer:
    def __init__(self):
        self.queue = Queue()
        self.worker = Thread(target=self._process_queue)
        self.worker.start()
    
    def _process_queue(self):
        """Process AI tasks one at a time"""
        while True:
            task = self.queue.get()
            try:
                result = self._analyze(task['channel'])
                task['callback'](result)
            except Exception as e:
                task['error_callback'](e)
            finally:
                time.sleep(0.2)  # Rate limiting
                self.queue.task_done()
    
    async def analyze_async(self, channel: dict) -> dict:
        """Submit analysis task"""
        future = asyncio.Future()
        
        self.queue.put({
            'channel': channel,
            'callback': lambda r: future.set_result(r),
            'error_callback': lambda e: future.set_exception(e)
        })
        
        return await future
```

### 5. Data Layer

#### MySQL Database

**Connection Pool**:

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

**Transaction Management**:

```python
async def update_channel_with_stats(channel_id, stats, analysis):
    """Atomic update with rollback"""
    async with async_session() as session:
        async with session.begin():
            try:
                # Update channel
                await session.execute(
                    update(Channel).where(
                        Channel.channel_id == channel_id
                    ).values(**stats)
                )
                
                # Insert analysis
                await session.execute(
                    insert(AIAnalysis).values(**analysis)
                )
                
                await session.commit()
            except Exception as e:
                await session.rollback()
                raise
```

#### Redis Cache

**Cache Hierarchy**:

```python
# L1: Channel basic info (permanent)
cache_key = f"channel:{channel_id}:info"
redis.set(cache_key, json.dumps(channel_data))  # No TTL

# L2: Video statistics (24h)
cache_key = f"channel:{channel_id}:stats"
redis.setex(cache_key, 86400, json.dumps(stats))

# L3: API quota tracking (reset daily)
quota_key = f"api_key:{api_key}:quota"
redis.setex(quota_key, time_until_midnight(), quota_used)
```

**Cache Invalidation**:

```python
def invalidate_channel_cache(channel_id: str):
    """Clear all cache for a channel"""
    pattern = f"channel:{channel_id}:*"
    keys = redis.keys(pattern)
    if keys:
        redis.delete(*keys)
```

## Data Flow

### Search Flow

```
User Input
    ├─ Keyword: "PC cleanup"
    └─ Mode: Normal/Accelerated
    
Task Creation
    ├─ Generate task_id
    ├─ Store in database
    └─ Emit WebSocket connection
    
YouTube Search (Phase 1)
    ├─ Search type=channel
    │   ├─ API call (100 units)
    │   ├─ Pagination loop
    │   └─ Collect channel IDs
    └─ Search type=video
        ├─ API call (100 units)
        ├─ Extract channel IDs
        └─ Merge with previous
    
Data Collection (Phase 2)
    ├─ Batch channel.list (1 unit / 50 channels)
    ├─ For each channel:
    │   ├─ Get uploads playlist (1 unit)
    │   ├─ Get recent videos (1 unit)
    │   ├─ Detect language (local)
    │   └─ Calculate stats (local)
    └─ Store to MySQL + Redis
    
AI Analysis (Phase 3)
    ├─ Queue unanalyzed channels
    ├─ Single-thread processing
    ├─ For each channel:
    │   ├─ Build prompt
    │   ├─ Call AI API
    │   ├─ Parse JSON response
    │   └─ Store result
    └─ Handle failures → retry queue
    
Result Display
    ├─ Progressive rendering
    ├─ Show basic data immediately
    ├─ Update with AI results as ready
    └─ Enable export when complete
```

### Incremental Update Flow

```
User Re-searches "PC cleanup"
    
System Detects Previous Search
    ├─ Query database for task with same keyword
    └─ Found task_id: ABC123
    
User Chooses: Incremental Update
    
Fetch Existing Channel IDs
    ├─ SELECT channel_id FROM channels 
    │   WHERE task_id = 'ABC123'
    └─ Result: [CH001, CH002, ..., CH500]
    
Execute New Search
    ├─ Search YouTube (same as before)
    └─ Get current channel IDs: [CH001, CH002, ..., CH500, CH501, CH502]
    
Compare & Identify
    ├─ New channels: [CH501, CH502]
    ├─ Still exist: [CH001, ..., CH500]
    └─ Disappeared: []
    
Process Only New Channels
    ├─ Collect data for CH501, CH502
    ├─ AI analyze CH501, CH502
    └─ Tag as "NEW" in database
    
Update UI
    ├─ Show all channels
    ├─ Highlight [NEW] channels
    └─ Update counts: "2 new channels found"
```

## Performance Optimization

### 1. Database Indexing

```sql
-- High-frequency query indexes
CREATE INDEX idx_channel_keyword ON channels(detected_language, subscriber_count);
CREATE INDEX idx_task_status ON search_tasks(status, created_at);
CREATE INDEX idx_analysis_score ON ai_analysis(relevance_score DESC);

-- Composite indexes for filtered queries
CREATE INDEX idx_channel_filter ON channels(subscriber_count, detected_language, status);
```

### 2. Query Optimization

```python
# Bad: N+1 query problem
channels = session.query(Channel).all()
for channel in channels:
    stats = session.query(VideoStats).filter_by(channel_id=channel.id).first()
    analysis = session.query(AIAnalysis).filter_by(channel_id=channel.id).first()

# Good: Eager loading
channels = session.query(Channel).options(
    joinedload(Channel.video_stats),
    joinedload(Channel.ai_analysis)
).all()
```

### 3. Caching Strategy

```python
@cache_result(ttl=86400, key_prefix="channel_stats")
async def get_channel_statistics(channel_id: str):
    """Cache expensive calculations"""
    # Complex aggregation query
    stats = await db.execute(complex_query)
    return stats
```

### 4. Async Optimization

```python
# Bad: Sequential API calls
for channel_id in channel_ids:
    data = await youtube_api.get_channel(channel_id)
    
# Good: Concurrent batch calls
tasks = [youtube_api.get_channel(cid) for cid in channel_ids]
results = await asyncio.gather(*tasks, return_exceptions=True)
```

## Security Considerations

### 1. API Key Protection

```python
# Never expose keys in responses
class APIKeyResponse(BaseModel):
    id: int
    key_preview: str  # Only show first/last 4 chars
    daily_quota: int
    used_quota: int
    is_active: bool
    
    @validator('key_preview', pre=True)
    def mask_key(cls, v):
        if len(v) > 8:
            return f"{v[:4]}...{v[-4:]}"
        return "****"
```

### 2. Input Validation

```python
from pydantic import BaseModel, validator

class SearchRequest(BaseModel):
    keyword: str
    accelerated: bool = False
    
    @validator('keyword')
    def validate_keyword(cls, v):
        if len(v) < 2:
            raise ValueError("Keyword too short")
        if len(v) > 100:
            raise ValueError("Keyword too long")
        # Sanitize for SQL injection
        if any(c in v for c in ["'", '"', ';', '--']):
            raise ValueError("Invalid characters")
        return v.strip()
```

### 3. Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/search/start")
@limiter.limit("10/minute")
async def start_search(request: Request):
    # Prevent abuse
    pass
```

## Monitoring & Observability

### 1. Logging

```python
import structlog

logger = structlog.get_logger()

async def search_channels(keyword: str):
    logger.info("search_started", keyword=keyword, task_id=task_id)
    
    try:
        results = await youtube_api.search(keyword)
        logger.info("search_completed", 
                   keyword=keyword, 
                   results_count=len(results))
    except Exception as e:
        logger.error("search_failed", 
                    keyword=keyword, 
                    error=str(e))
        raise
```

### 2. Metrics

```python
from prometheus_client import Counter, Histogram

# API call metrics
api_calls_total = Counter('youtube_api_calls_total', 
                         'Total YouTube API calls',
                         ['endpoint', 'status'])

api_call_duration = Histogram('youtube_api_call_duration_seconds',
                             'YouTube API call duration')

@api_call_duration.time()
async def call_youtube_api(endpoint: str):
    try:
        result = await api_client.call(endpoint)
        api_calls_total.labels(endpoint=endpoint, status='success').inc()
        return result
    except Exception:
        api_calls_total.labels(endpoint=endpoint, status='error').inc()
        raise
```

### 3. Health Checks

```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": await check_database(),
        "redis": await check_redis(),
        "youtube_api": await check_youtube_api(),
        "ai_api": await check_ai_api()
    }
```

## Scalability

### Horizontal Scaling

```yaml
# docker-compose scale example
services:
  api:
    image: youtube-kol-api
    deploy:
      replicas: 3
    
  worker:
    image: youtube-kol-worker
    deploy:
      replicas: 5
```

### Load Balancing

```nginx
upstream api_cluster {
    least_conn;
    server api1:8000;
    server api2:8000;
    server api3:8000;
}
```

This architecture supports:
- 1000+ concurrent searches
- 100,000+ channels in database
- 10,000+ API calls per day (per key)
- Real-time updates for 100+ connected users
