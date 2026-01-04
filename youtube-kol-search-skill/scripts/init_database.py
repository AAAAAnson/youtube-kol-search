#!/usr/bin/env python3
"""
Initialize MySQL database schema for YouTube KOL Search System

Usage:
    python init_database.py [--host HOST] [--port PORT] [--user USER] [--password PASSWORD] [--database DATABASE]
"""

import argparse
import sys
from pathlib import Path
import mysql.connector
from mysql.connector import Error
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_database(connection, database_name):
    """Create database if not exists"""
    try:
        cursor = connection.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        logger.info(f"✓ Database '{database_name}' ready")
        cursor.close()
    except Error as e:
        logger.error(f"✗ Failed to create database: {e}")
        raise


def create_tables(connection):
    """Create all required tables"""
    
    cursor = connection.cursor()
    
    tables = {
        'search_tasks': """
            CREATE TABLE IF NOT EXISTS search_tasks (
                id INT PRIMARY KEY AUTO_INCREMENT,
                task_id VARCHAR(64) UNIQUE NOT NULL COMMENT 'UUID for task tracking',
                keyword VARCHAR(255) NOT NULL COMMENT 'Search keyword',
                product_info TEXT COMMENT 'Product information snapshot',
                status ENUM('pending', 'running', 'completed', 'failed', 'paused') DEFAULT 'pending',
                total_channels INT DEFAULT 0,
                processed_channels INT DEFAULT 0,
                is_incremental BOOLEAN DEFAULT 0,
                parent_task_id VARCHAR(64),
                new_channels_count INT DEFAULT 0,
                accelerated_mode BOOLEAN DEFAULT 0,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP NULL,
                completed_at TIMESTAMP NULL,
                
                INDEX idx_keyword (keyword),
                INDEX idx_status (status),
                INDEX idx_created (created_at DESC),
                INDEX idx_parent (parent_task_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        
        'channels': """
            CREATE TABLE IF NOT EXISTS channels (
                id INT PRIMARY KEY AUTO_INCREMENT,
                channel_id VARCHAR(64) UNIQUE NOT NULL,
                channel_title VARCHAR(255) NOT NULL,
                channel_url VARCHAR(512) NOT NULL,
                subscriber_count BIGINT DEFAULT 0,
                description TEXT,
                detected_language VARCHAR(10),
                language_confidence FLOAT,
                custom_url VARCHAR(255),
                thumbnail_url VARCHAR(512),
                first_discovered_at TIMESTAMP NOT NULL,
                last_seen_at TIMESTAMP NOT NULL,
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
        """,
        
        'channel_video_stats': """
            CREATE TABLE IF NOT EXISTS channel_video_stats (
                id INT PRIMARY KEY AUTO_INCREMENT,
                channel_id VARCHAR(64) NOT NULL,
                task_id VARCHAR(64) NOT NULL,
                avg_view_count BIGINT DEFAULT 0,
                avg_like_count INT DEFAULT 0,
                avg_comment_count INT DEFAULT 0,
                avg_engagement_rate FLOAT DEFAULT 0,
                has_outliers BOOLEAN DEFAULT 0,
                outlier_videos JSON,
                recent_videos JSON NOT NULL,
                video_languages JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                INDEX idx_channel_task (channel_id, task_id),
                INDEX idx_engagement (avg_engagement_rate DESC),
                INDEX idx_views (avg_view_count DESC)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        
        'ai_analysis': """
            CREATE TABLE IF NOT EXISTS ai_analysis (
                id INT PRIMARY KEY AUTO_INCREMENT,
                channel_id VARCHAR(64) NOT NULL,
                task_id VARCHAR(64) NOT NULL,
                relevance_score INT,
                audience_match TEXT,
                content_alignment TEXT,
                recommendation TEXT,
                key_strengths JSON,
                concerns JSON,
                analysis_detail JSON NOT NULL,
                ai_provider VARCHAR(20),
                analysis_status ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'pending',
                error_message TEXT,
                analyzed_at TIMESTAMP NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                INDEX idx_channel_task (channel_id, task_id),
                INDEX idx_score (relevance_score DESC),
                INDEX idx_status (analysis_status),
                INDEX idx_provider (ai_provider),
                UNIQUE KEY uk_channel_task (channel_id, task_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        
        'api_keys': """
            CREATE TABLE IF NOT EXISTS api_keys (
                id INT PRIMARY KEY AUTO_INCREMENT,
                api_key VARCHAR(512) NOT NULL,
                api_type ENUM('youtube', 'deepseek', 'zhipu') NOT NULL,
                display_name VARCHAR(100),
                daily_quota INT DEFAULT 10000,
                used_quota INT DEFAULT 0,
                last_reset_date DATE,
                is_active BOOLEAN DEFAULT 1,
                priority INT DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                
                INDEX idx_type_active (api_type, is_active),
                INDEX idx_quota (used_quota, daily_quota),
                INDEX idx_priority (priority DESC),
                UNIQUE KEY uk_api_key (api_key(255))
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        
        'product_config': """
            CREATE TABLE IF NOT EXISTS product_config (
                id INT PRIMARY KEY AUTO_INCREMENT,
                product_name VARCHAR(255) NOT NULL,
                product_url VARCHAR(512),
                product_description TEXT,
                core_features JSON,
                target_audience TEXT,
                keywords JSON,
                auto_scraped_content TEXT,
                last_scraped_at TIMESTAMP NULL,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                
                INDEX idx_active (is_active),
                FULLTEXT INDEX ft_description (product_description, auto_scraped_content)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    }
    
    for table_name, create_sql in tables.items():
        try:
            cursor.execute(create_sql)
            logger.info(f"✓ Table '{table_name}' created")
        except Error as e:
            logger.error(f"✗ Failed to create table '{table_name}': {e}")
            raise
    
    cursor.close()


def add_foreign_keys(connection):
    """Add foreign key constraints"""
    
    cursor = connection.cursor()
    
    constraints = [
        """
        ALTER TABLE search_tasks
        ADD CONSTRAINT fk_parent_task
        FOREIGN KEY (parent_task_id) REFERENCES search_tasks(task_id)
        ON DELETE SET NULL
        """,
        
        """
        ALTER TABLE channel_video_stats
        ADD CONSTRAINT fk_stats_channel
        FOREIGN KEY (channel_id) REFERENCES channels(channel_id)
        ON DELETE CASCADE
        """,
        
        """
        ALTER TABLE channel_video_stats
        ADD CONSTRAINT fk_stats_task
        FOREIGN KEY (task_id) REFERENCES search_tasks(task_id)
        ON DELETE CASCADE
        """,
        
        """
        ALTER TABLE ai_analysis
        ADD CONSTRAINT fk_analysis_channel
        FOREIGN KEY (channel_id) REFERENCES channels(channel_id)
        ON DELETE CASCADE
        """,
        
        """
        ALTER TABLE ai_analysis
        ADD CONSTRAINT fk_analysis_task
        FOREIGN KEY (task_id) REFERENCES search_tasks(task_id)
        ON DELETE CASCADE
        """
    ]
    
    for constraint_sql in constraints:
        try:
            cursor.execute(constraint_sql)
            logger.info("✓ Foreign key constraint added")
        except Error as e:
            # Ignore if constraint already exists
            if "Duplicate" not in str(e):
                logger.warning(f"⚠ Constraint warning: {e}")
    
    cursor.close()


def seed_initial_data(connection):
    """Insert initial configuration data"""
    
    cursor = connection.cursor()
    
    # Insert default product config
    try:
        cursor.execute("""
            INSERT INTO product_config (
                product_name, 
                product_url, 
                product_description,
                core_features,
                target_audience,
                keywords,
                is_active
            ) VALUES (
                'WMaster Cleanup',
                'https://www.wmastercleanup.com/',
                'All-in-One Windows Cleaner & Optimizer for cleaning junk files, freeing disk space, and improving PC performance',
                '["Disk cleanup", "Duplicate file removal", "Application uninstaller", "Cache clearing", "Privacy protection"]',
                'Windows users who want to optimize PC performance, free up disk space, and maintain system health',
                '["PC cleanup", "Windows optimizer", "disk cleaner", "system speedup", "junk file removal"]',
                1
            )
            ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP
        """)
        logger.info("✓ Default product config seeded")
    except Error as e:
        logger.warning(f"⚠ Product config already exists or error: {e}")
    
    connection.commit()
    cursor.close()


def create_schema_version_table(connection):
    """Create schema migrations tracking table"""
    
    cursor = connection.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INT PRIMARY KEY,
            description VARCHAR(255),
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB
    """)
    
    cursor.execute("""
        INSERT IGNORE INTO schema_migrations (version, description) VALUES
        (1, 'Initial schema'),
        (2, 'Add incremental update support'),
        (3, 'Add AI provider field'),
        (4, 'Add language detection confidence')
    """)
    
    logger.info("✓ Schema version tracking ready")
    connection.commit()
    cursor.close()


def main():
    parser = argparse.ArgumentParser(description='Initialize YouTube KOL Search database')
    parser.add_argument('--host', default='localhost', help='MySQL host')
    parser.add_argument('--port', type=int, default=3306, help='MySQL port')
    parser.add_argument('--user', default='root', help='MySQL user')
    parser.add_argument('--password', required=True, help='MySQL password')
    parser.add_argument('--database', default='youtube_kol_db', help='Database name')
    
    args = parser.parse_args()
    
    try:
        # Connect to MySQL server
        logger.info(f"Connecting to MySQL at {args.host}:{args.port}...")
        connection = mysql.connector.connect(
            host=args.host,
            port=args.port,
            user=args.user,
            password=args.password
        )
        
        if connection.is_connected():
            logger.info("✓ Connected to MySQL server")
            
            # Create database
            create_database(connection, args.database)
            
            # Switch to the database
            connection.database = args.database
            
            # Create tables
            logger.info("\nCreating tables...")
            create_tables(connection)
            
            # Add foreign keys
            logger.info("\nAdding foreign key constraints...")
            add_foreign_keys(connection)
            
            # Seed initial data
            logger.info("\nSeeding initial data...")
            seed_initial_data(connection)
            
            # Create schema version table
            logger.info("\nSetting up schema versioning...")
            create_schema_version_table(connection)
            
            logger.info("\n✅ Database initialization completed successfully!")
            logger.info(f"\nDatabase: {args.database}")
            logger.info("Next steps:")
            logger.info("1. Copy .env.example to .env")
            logger.info("2. Add your API keys via the web interface")
            logger.info("3. Start the application with: docker-compose up -d")
            
    except Error as e:
        logger.error(f"\n❌ Database initialization failed: {e}")
        sys.exit(1)
    
    finally:
        if connection and connection.is_connected():
            connection.close()
            logger.info("\n✓ MySQL connection closed")


if __name__ == '__main__':
    main()
