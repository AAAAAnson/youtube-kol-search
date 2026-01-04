# Database Schema

Complete MySQL database schema for the YouTube KOL Search System.

## Entity-Relationship Diagram

```
┌─────────────────┐         ┌──────────────────┐
│  search_tasks   │         │   api_keys       │
│─────────────────│         │──────────────────│
│ id (PK)         │         │ id (PK)          │
│ task_id (UK)    │         │ api_key          │
│ keyword         │         │ api_type         │
│ product_info    │         │ daily_quota      │
│ status          │         │ used_quota       │
│ total_channels  │         │ last_reset_date  │
│ processed_ch... │         │ is_active        │
│ is_incremental  │         │ created_at       │
│ parent_task_id  │         └──────────────────┘
│ new_channels... │
│ created_at      │
│ completed_at    │
└────────┬────────┘
         │ 1
         │
         │ N
┌────────┴──────────┐        ┌──────────────────┐
│   channels        │────N───│ channel_video_   │
│───────────────────│   1    │     stats        │
│ id (PK)           │        │──────────────────│
│ channel_id (UK)   │        │ id (PK)          │
│ channel_title     │        │ channel_id (FK)  │
│ channel_url       │        │ task_id          │
│ subscriber_count  │        │ avg_view_count   │
│ description       │        │ avg_like_count   │
│ detected_language │        │ avg_comment_count│
│ language_confid...│        │ avg_engagement...│
│ custom_url        │        │ has_outliers     │
│ thumbnail_url     │        │ outlier_videos   │
│ first_discovered..│        │ recent_videos    │
│ last_seen_at      │        │ video_languages  │
│ status            │        │ created_at       │
│ created_at        │        └──────────────────┘
│ updated_at        │
└────────┬──────────┘
         │ 1
         │
         │ N
┌────────┴──────────┐
│   ai_analysis     │
│───────────────────│
│ id (PK)           │
│ channel_id (FK)   │
│ task_id           │
│ relevance_score   │
│ audience_match    │
│ recommendation    │
│ analysis_detail   │
│ ai_provider       │
│ analysis_status   │
│ analyzed_at       │
└───────────────────┘

┌─────────────────────┐
│  product_config     │
│─────────────────────│
│ id (PK)             │
│ product_name        │
│ product_url         │
│ product_description │
│ core_features (JSON)│
│ target_audience     │
│ keywords (JSON)     │
│ auto_scraped_content│
│ last_scraped_at     │
│ is_active           │
│ created_at          │
│ updated_at          │
└─────────────────────┘
```

## Table Definitions

### 1. search_tasks

Stores search task metadata and execution status.

```sql
CREATE TABLE search_tasks (
    id INT PRIMARY KEY AUTO_INCREMENT,
    task_id VARCHAR(64) UNIQUE NOT NULL COMMENT 'UUID for task tracking',
    keyword VARCHAR(255) NOT NULL COMMENT 'Search keyword',
    product_info TEXT COMMENT 'Product information snapshot at search time',
    status ENUM('pending', 'running', 'completed', 'failed', 'paused') DEFAULT 'pending',
    total_channels INT DEFAULT 0 COMMENT 'Total channels found',
    processed_channels INT DEFAULT 0 COMMENT 'Channels processed so far',
    is_incremental BOOLEAN DEFAULT 0 COMMENT 'Is this an incremental update',
    parent_task_id VARCHAR(64) COMMENT 'Parent task ID if incremental',
    new_channels_count INT DEFAULT 0 COMMENT 'New channels in incremental update',
    accelerated_mode BOOLEAN DEFAULT 0 COMMENT 'Was accelerated mode used',
    error_message TEXT COMMENT 'Error details if failed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP NULL COMMENT 'Actual start time',
    completed_at TIMESTAMP NULL COMMENT 'Completion time',
    
    INDEX idx_keyword (keyword),
    INDEX idx_status (status),
    INDEX idx_created (created_at DESC),
    INDEX idx_parent (parent_task_id),
    
    FOREIGN KEY (parent_task_id) REFERENCES search_tasks(task_id) 
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Search task tracking';
```

**Key Columns**:
- `task_id`: UUID generated at task creation, used for WebSocket subscriptions
- `is_incremental`: Marks incremental vs full searches
- `parent_task_id`: Links to previous search for same keyword
- `accelerated_mode`: Tracks if faster (riskier) mode was used

### 2. channels

Stores YouTube channel basic information.

```sql
CREATE TABLE channels (
    id INT PRIMARY KEY AUTO_INCREMENT,
    channel_id VARCHAR(64) UNIQUE NOT NULL COMMENT 'YouTube channel ID',
    channel_title VARCHAR(255) NOT NULL COMMENT 'Channel name',
    channel_url VARCHAR(512) NOT NULL COMMENT 'Channel URL',
    subscriber_count BIGINT DEFAULT 0 COMMENT 'Subscriber count at last check',
    description TEXT COMMENT 'Channel description',
    detected_language VARCHAR(10) COMMENT 'Primary language (ISO 639-1)',
    language_confidence FLOAT COMMENT 'Language detection confidence (0-1)',
    custom_url VARCHAR(255) COMMENT 'Channel custom URL',
    thumbnail_url VARCHAR(512) COMMENT 'Channel thumbnail image URL',
    first_discovered_at TIMESTAMP NOT NULL COMMENT 'First time channel was found',
    last_seen_at TIMESTAMP NOT NULL COMMENT 'Last time channel appeared in search',
    status ENUM('active', 'disappeared', 'deleted', 'private') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_channel_id (channel_id),
    INDEX idx_language (detected_language),
    INDEX idx_subscribers (subscriber_count DESC),
    INDEX idx_status (status),
    INDEX idx_last_seen (last_seen_at DESC),
    
    FULLTEXT INDEX ft_title_desc (channel_title, description)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='YouTube channel basic information';
```

**Key Columns**:
- `detected_language`: Result of comprehensive language detection (Method B)
- `language_confidence`: Higher values = more confident detection
- `first_discovered_at`: For tracking when channel was first found
- `last_seen_at`: Updated each time channel appears in search
- `status`: Lifecycle tracking (active, disappeared, deleted, private)

**Indexes**:
- Composite index on `(detected_language, subscriber_count)` for filtered queries
- FULLTEXT index for channel name/description searches

### 3. channel_video_stats

Stores aggregated statistics from recent videos.

```sql
CREATE TABLE channel_video_stats (
    id INT PRIMARY KEY AUTO_INCREMENT,
    channel_id VARCHAR(64) NOT NULL COMMENT 'Reference to channels table',
    task_id VARCHAR(64) NOT NULL COMMENT 'Task that generated this data',
    avg_view_count BIGINT DEFAULT 0 COMMENT 'Average views of recent 10 videos',
    avg_like_count INT DEFAULT 0 COMMENT 'Average likes',
    avg_comment_count INT DEFAULT 0 COMMENT 'Average comments',
    avg_engagement_rate FLOAT DEFAULT 0 COMMENT '(likes+comments)/views average',
    has_outliers BOOLEAN DEFAULT 0 COMMENT 'Contains anomalous videos',
    outlier_videos JSON COMMENT 'List of outlier video details',
    recent_videos JSON NOT NULL COMMENT 'Full data of recent 10 videos',
    video_languages JSON COMMENT 'Language distribution {"en": 7, "zh": 3}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_channel_task (channel_id, task_id),
    INDEX idx_engagement (avg_engagement_rate DESC),
    INDEX idx_views (avg_view_count DESC),
    
    FOREIGN KEY (channel_id) REFERENCES channels(channel_id) 
        ON DELETE CASCADE,
    FOREIGN KEY (task_id) REFERENCES search_tasks(task_id) 
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Channel video statistics';
```

**JSON Structure Examples**:

```json
// outlier_videos
[
  {
    "video_id": "abc123",
    "title": "Viral video",
    "view_count": 5000000,
    "reason": "significantly_higher"
  }
]

// recent_videos
[
  {
    "video_id": "vid001",
    "title": "Video title",
    "description": "Video description...",
    "view_count": 10000,
    "like_count": 500,
    "comment_count": 50,
    "engagement_rate": 0.055,
    "language": "en",
    "published_at": "2024-01-15T10:30:00Z"
  }
]

// video_languages
{
  "en": 7,
  "zh": 2,
  "ja": 1
}
```

### 4. ai_analysis

Stores AI evaluation results for channel-product fit.

```sql
CREATE TABLE ai_analysis (
    id INT PRIMARY KEY AUTO_INCREMENT,
    channel_id VARCHAR(64) NOT NULL COMMENT 'Reference to channels table',
    task_id VARCHAR(64) NOT NULL COMMENT 'Task that triggered analysis',
    relevance_score INT COMMENT 'Content relevance (0-100)',
    audience_match TEXT COMMENT 'Audience alignment analysis',
    content_alignment TEXT COMMENT 'Content relevance analysis',
    recommendation TEXT COMMENT 'Marketing recommendation',
    key_strengths JSON COMMENT 'Array of strength points',
    concerns JSON COMMENT 'Array of concerns',
    analysis_detail JSON NOT NULL COMMENT 'Full AI response',
    ai_provider VARCHAR(20) COMMENT 'deepseek or zhipu',
    analysis_status ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'pending',
    error_message TEXT COMMENT 'Error if analysis failed',
    analyzed_at TIMESTAMP NULL COMMENT 'When analysis completed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_channel_task (channel_id, task_id),
    INDEX idx_score (relevance_score DESC),
    INDEX idx_status (analysis_status),
    INDEX idx_provider (ai_provider),
    
    FOREIGN KEY (channel_id) REFERENCES channels(channel_id) 
        ON DELETE CASCADE,
    FOREIGN KEY (task_id) REFERENCES search_tasks(task_id) 
        ON DELETE CASCADE,
    
    UNIQUE KEY uk_channel_task (channel_id, task_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='AI-powered channel analysis results';
```

**JSON Structure Example**:

```json
// analysis_detail
{
  "relevance_score": 85,
  "audience_match": "Strong alignment with Windows users seeking PC optimization",
  "content_alignment": "Channel focuses on tech tutorials and software reviews",
  "recommendation": "Highly recommended for sponsored content integration",
  "key_strengths": [
    "Consistent content about PC performance",
    "Engaged audience with high interaction rates",
    "Professional production quality"
  ],
  "concerns": [
    "Recent decrease in upload frequency",
    "Limited coverage of cleanup tools specifically"
  ],
  "prompt_used": "...",
  "model_version": "deepseek-chat",
  "tokens_used": 1250
}
```

### 5. api_keys

Manages YouTube and AI API keys with quota tracking.

```sql
CREATE TABLE api_keys (
    id INT PRIMARY KEY AUTO_INCREMENT,
    api_key VARCHAR(512) NOT NULL COMMENT 'Encrypted API key',
    api_type ENUM('youtube', 'deepseek', 'zhipu') NOT NULL,
    display_name VARCHAR(100) COMMENT 'User-friendly name',
    daily_quota INT DEFAULT 10000 COMMENT 'Daily quota limit',
    used_quota INT DEFAULT 0 COMMENT 'Used quota today',
    last_reset_date DATE COMMENT 'Last quota reset date',
    is_active BOOLEAN DEFAULT 1 COMMENT 'Is this key active',
    priority INT DEFAULT 0 COMMENT 'Higher priority used first',
    notes TEXT COMMENT 'Admin notes about this key',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_type_active (api_type, is_active),
    INDEX idx_quota (used_quota, daily_quota),
    INDEX idx_priority (priority DESC),
    
    UNIQUE KEY uk_api_key (api_key(255))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='API key management with quota tracking';
```

**Key Features**:
- `priority`: Allows manual ordering of which keys to use first
- `last_reset_date`: Tracks when quota was last reset to 0
- `api_type`: Supports both YouTube and AI API keys in same table

### 6. product_config

Stores product information for AI analysis.

```sql
CREATE TABLE product_config (
    id INT PRIMARY KEY AUTO_INCREMENT,
    product_name VARCHAR(255) NOT NULL,
    product_url VARCHAR(512),
    product_description TEXT COMMENT 'Manual product description',
    core_features JSON COMMENT 'Array of key features',
    target_audience TEXT COMMENT 'Target user description',
    keywords JSON COMMENT 'Array of relevant keywords',
    auto_scraped_content TEXT COMMENT 'Auto-scraped website content',
    last_scraped_at TIMESTAMP NULL COMMENT 'Last auto-scrape time',
    is_active BOOLEAN DEFAULT 1 COMMENT 'Is this the active product',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_active (is_active),
    
    FULLTEXT INDEX ft_description (product_description, auto_scraped_content)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Product configuration for AI analysis';
```

**JSON Structure Example**:

```json
// core_features
[
  "Disk cleanup and optimization",
  "Duplicate file removal",
  "Application uninstaller",
  "Privacy protection",
  "Registry cleaner"
]

// keywords
[
  "PC cleanup",
  "Windows optimizer",
  "disk space",
  "system cleaner",
  "computer speedup"
]
```

## Queries

### Common Query Patterns

#### 1. Get Channels with Full Details

```sql
SELECT 
    c.channel_id,
    c.channel_title,
    c.channel_url,
    c.subscriber_count,
    c.detected_language,
    c.status,
    vs.avg_view_count,
    vs.avg_engagement_rate,
    vs.has_outliers,
    ai.relevance_score,
    ai.recommendation,
    ai.analysis_status
FROM channels c
LEFT JOIN channel_video_stats vs ON c.channel_id = vs.channel_id
LEFT JOIN ai_analysis ai ON c.channel_id = ai.channel_id
WHERE vs.task_id = :task_id
ORDER BY c.subscriber_count DESC;
```

#### 2. Find Top Performing Channels

```sql
SELECT 
    c.channel_title,
    c.subscriber_count,
    vs.avg_engagement_rate,
    ai.relevance_score,
    (
        (c.subscriber_count / 1000000) * 0.3 +  -- Subscriber weight
        (vs.avg_engagement_rate * 100) * 0.3 +   -- Engagement weight
        (ai.relevance_score / 100) * 0.4         -- AI score weight
    ) AS composite_score
FROM channels c
JOIN channel_video_stats vs ON c.channel_id = vs.channel_id
JOIN ai_analysis ai ON c.channel_id = ai.channel_id
WHERE ai.relevance_score >= 70
  AND c.detected_language = 'en'
  AND c.status = 'active'
ORDER BY composite_score DESC
LIMIT 20;
```

#### 3. Incremental Update Detection

```sql
-- Get new channels from latest search
SELECT c.*, 'NEW' as tag
FROM channels c
JOIN channel_video_stats vs ON c.channel_id = vs.channel_id
WHERE vs.task_id = :new_task_id
  AND NOT EXISTS (
      SELECT 1 FROM channel_video_stats vs2
      WHERE vs2.channel_id = c.channel_id
        AND vs2.task_id = :parent_task_id
  );
```

#### 4. Channel Language Distribution

```sql
SELECT 
    detected_language,
    COUNT(*) as channel_count,
    AVG(subscriber_count) as avg_subscribers,
    AVG(avg_engagement_rate) as avg_engagement
FROM channels c
JOIN channel_video_stats vs ON c.channel_id = vs.channel_id
WHERE vs.task_id = :task_id
GROUP BY detected_language
ORDER BY channel_count DESC;
```

#### 5. Pending AI Analysis

```sql
SELECT c.channel_id, c.channel_title
FROM channels c
JOIN channel_video_stats vs ON c.channel_id = vs.channel_id
LEFT JOIN ai_analysis ai ON c.channel_id = ai.channel_id 
    AND ai.task_id = :task_id
WHERE vs.task_id = :task_id
  AND (ai.id IS NULL OR ai.analysis_status = 'failed')
ORDER BY c.subscriber_count DESC;
```

#### 6. API Key Quota Status

```sql
SELECT 
    id,
    display_name,
    api_type,
    used_quota,
    daily_quota,
    (daily_quota - used_quota) as remaining_quota,
    ROUND((used_quota / daily_quota * 100), 2) as usage_percent,
    last_reset_date,
    CASE 
        WHEN last_reset_date < CURDATE() THEN 'NEEDS_RESET'
        WHEN used_quota >= daily_quota THEN 'EXHAUSTED'
        WHEN used_quota >= daily_quota * 0.9 THEN 'WARNING'
        ELSE 'OK'
    END as status
FROM api_keys
WHERE is_active = 1
  AND api_type = 'youtube'
ORDER BY priority DESC, remaining_quota DESC;
```

## Data Maintenance

### Daily Cleanup Job

```sql
-- Archive old search tasks (keep last 90 days)
DELETE FROM search_tasks 
WHERE created_at < DATE_SUB(NOW(), INTERVAL 90 DAY)
  AND status != 'running';

-- Mark disappeared channels (not seen in 30 days)
UPDATE channels
SET status = 'disappeared'
WHERE last_seen_at < DATE_SUB(NOW(), INTERVAL 30 DAY)
  AND status = 'active';

-- Reset API key quotas (run at UTC midnight)
UPDATE api_keys
SET used_quota = 0,
    last_reset_date = CURDATE()
WHERE last_reset_date < CURDATE();
```

### Vacuum & Optimize

```sql
-- Monthly optimization
OPTIMIZE TABLE channels;
OPTIMIZE TABLE channel_video_stats;
OPTIMIZE TABLE ai_analysis;

-- Rebuild indexes if needed
ANALYZE TABLE channels;
ANALYZE TABLE search_tasks;
```

## Backup Strategy

### Daily Incremental Backup

```bash
#!/bin/bash
# Backup only changed data
mysqldump --single-transaction \
          --where="created_at >= CURDATE() - INTERVAL 1 DAY" \
          youtube_kol_db \
          channels channel_video_stats ai_analysis \
          > backup_$(date +%Y%m%d).sql
```

### Weekly Full Backup

```bash
#!/bin/bash
# Full database backup
mysqldump --single-transaction \
          --routines \
          --triggers \
          youtube_kol_db \
          | gzip > backup_full_$(date +%Y%m%d).sql.gz
```

## Performance Tuning

### MySQL Configuration

```ini
[mysqld]
# InnoDB settings
innodb_buffer_pool_size = 2G
innodb_log_file_size = 512M
innodb_flush_log_at_trx_commit = 2
innodb_flush_method = O_DIRECT

# Query cache (for frequent reads)
query_cache_type = 1
query_cache_size = 256M

# Connection pool
max_connections = 200
thread_cache_size = 100

# Temp tables
tmp_table_size = 128M
max_heap_table_size = 128M
```

### Partitioning (for large datasets)

```sql
-- Partition search_tasks by month
ALTER TABLE search_tasks
PARTITION BY RANGE (YEAR(created_at) * 100 + MONTH(created_at)) (
    PARTITION p202401 VALUES LESS THAN (202402),
    PARTITION p202402 VALUES LESS THAN (202403),
    -- ... add partitions as needed
    PARTITION p_future VALUES LESS THAN MAXVALUE
);
```

## Migration Scripts

### Initial Schema Setup

```sql
-- Run in order:
SOURCE 01_create_tables.sql;
SOURCE 02_create_indexes.sql;
SOURCE 03_create_constraints.sql;
SOURCE 04_seed_data.sql;
```

### Schema Version Tracking

```sql
CREATE TABLE schema_migrations (
    version INT PRIMARY KEY,
    description VARCHAR(255),
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO schema_migrations (version, description) VALUES
(1, 'Initial schema'),
(2, 'Add incremental update support'),
(3, 'Add AI provider field'),
(4, 'Add language detection confidence');
```

This schema supports:
- Millions of channels
- Thousands of concurrent searches
- Full audit trail
- Efficient querying and filtering
- Data integrity with foreign keys
- Flexible JSON storage for complex data
