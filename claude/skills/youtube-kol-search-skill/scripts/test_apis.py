#!/usr/bin/env python3
"""
Test YouTube and AI API connectivity

Usage:
    python test_apis.py --youtube-key YOUR_KEY --ai-provider deepseek --ai-key YOUR_AI_KEY
"""

import argparse
import sys
import json
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import requests
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_youtube_api(api_key: str) -> bool:
    """Test YouTube Data API v3 connectivity and quota"""
    
    logger.info("\n🔍 Testing YouTube API...")
    
    try:
        # Build YouTube service
        youtube = build('youtube', 'v3', developerKey=api_key)
        
        # Test 1: Simple search (costs 100 units)
        logger.info("  → Testing search endpoint...")
        search_response = youtube.search().list(
            q='test',
            part='snippet',
            maxResults=1,
            type='channel'
        ).execute()
        
        if search_response.get('items'):
            logger.info("  ✓ Search endpoint working")
        else:
            logger.warning("  ⚠ Search returned no results (unusual)")
        
        # Test 2: Get channel details (costs 1 unit)
        logger.info("  → Testing channels endpoint...")
        if search_response.get('items'):
            channel_id = search_response['items'][0]['snippet']['channelId']
            channel_response = youtube.channels().list(
                part='snippet,statistics',
                id=channel_id
            ).execute()
            
            if channel_response.get('items'):
                channel = channel_response['items'][0]
                logger.info(f"  ✓ Channels endpoint working")
                logger.info(f"     Sample channel: {channel['snippet']['title']}")
                logger.info(f"     Subscribers: {channel['statistics'].get('subscriberCount', 'N/A')}")
        
        # Test 3: Get playlist items (costs 1 unit)
        logger.info("  → Testing playlistItems endpoint...")
        uploads_playlist_id = channel['contentDetails']['relatedPlaylists']['uploads']
        playlist_response = youtube.playlistItems().list(
            part='contentDetails',
            playlistId=uploads_playlist_id,
            maxResults=1
        ).execute()
        
        if playlist_response.get('items'):
            logger.info("  ✓ PlaylistItems endpoint working")
        
        # Test 4: Get video details (costs 1 unit)
        logger.info("  → Testing videos endpoint...")
        if playlist_response.get('items'):
            video_id = playlist_response['items'][0]['contentDetails']['videoId']
            video_response = youtube.videos().list(
                part='statistics,snippet',
                id=video_id
            ).execute()
            
            if video_response.get('items'):
                logger.info("  ✓ Videos endpoint working")
                video = video_response['items'][0]
                logger.info(f"     Sample video: {video['snippet']['title']}")
                logger.info(f"     Views: {video['statistics'].get('viewCount', 'N/A')}")
        
        logger.info("\n✅ YouTube API: ALL TESTS PASSED")
        logger.info("   Estimated quota used: ~103 units (out of 10,000 daily)")
        return True
        
    except HttpError as e:
        error_details = json.loads(e.content)
        error_message = error_details.get('error', {}).get('message', str(e))
        
        if e.resp.status == 403:
            logger.error("\n❌ YouTube API: AUTHENTICATION FAILED")
            logger.error(f"   Error: {error_message}")
            logger.error("   Possible causes:")
            logger.error("   1. Invalid API key")
            logger.error("   2. YouTube Data API v3 not enabled in Google Cloud Console")
            logger.error("   3. Quota exceeded (check console)")
        else:
            logger.error(f"\n❌ YouTube API: HTTP {e.resp.status} ERROR")
            logger.error(f"   {error_message}")
        
        return False
        
    except Exception as e:
        logger.error(f"\n❌ YouTube API: UNEXPECTED ERROR")
        logger.error(f"   {str(e)}")
        return False


def test_deepseek_api(api_key: str) -> bool:
    """Test Deepseek AI API connectivity"""
    
    logger.info("\n🤖 Testing Deepseek AI API...")
    
    try:
        # Test simple completion
        logger.info("  → Sending test prompt...")
        
        response = requests.post(
            'https://api.deepseek.com/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'deepseek-chat',
                'messages': [
                    {
                        'role': 'user',
                        'content': 'Respond with only "OK" if you receive this message.'
                    }
                ],
                'max_tokens': 10
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            logger.info("  ✓ API connection successful")
            logger.info(f"     Response: {content}")
            logger.info(f"     Model: {result.get('model', 'N/A')}")
            logger.info(f"     Tokens used: {result.get('usage', {}).get('total_tokens', 'N/A')}")
            
            logger.info("\n✅ Deepseek API: ALL TESTS PASSED")
            return True
        else:
            logger.error(f"\n❌ Deepseek API: HTTP {response.status_code}")
            logger.error(f"   {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        logger.error("\n❌ Deepseek API: CONNECTION TIMEOUT")
        logger.error("   The API took too long to respond (>30s)")
        return False
        
    except requests.exceptions.RequestException as e:
        logger.error("\n❌ Deepseek API: CONNECTION ERROR")
        logger.error(f"   {str(e)}")
        return False
        
    except Exception as e:
        logger.error(f"\n❌ Deepseek API: UNEXPECTED ERROR")
        logger.error(f"   {str(e)}")
        return False


def test_zhipu_api(api_key: str) -> bool:
    """Test Zhipu AI API connectivity"""
    
    logger.info("\n🤖 Testing Zhipu AI API...")
    
    try:
        # Test simple completion
        logger.info("  → Sending test prompt...")
        
        response = requests.post(
            'https://open.bigmodel.cn/api/paas/v4/chat/completions',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'glm-4',
                'messages': [
                    {
                        'role': 'user',
                        'content': 'Respond with only "OK" if you receive this message.'
                    }
                ],
                'max_tokens': 10
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            logger.info("  ✓ API connection successful")
            logger.info(f"     Response: {content}")
            logger.info(f"     Model: {result.get('model', 'N/A')}")
            logger.info(f"     Tokens used: {result.get('usage', {}).get('total_tokens', 'N/A')}")
            
            logger.info("\n✅ Zhipu AI API: ALL TESTS PASSED")
            return True
        else:
            logger.error(f"\n❌ Zhipu AI API: HTTP {response.status_code}")
            logger.error(f"   {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        logger.error("\n❌ Zhipu AI API: CONNECTION TIMEOUT")
        logger.error("   The API took too long to respond (>30s)")
        return False
        
    except requests.exceptions.RequestException as e:
        logger.error("\n❌ Zhipu AI API: CONNECTION ERROR")
        logger.error(f"   {str(e)}")
        return False
        
    except Exception as e:
        logger.error(f"\n❌ Zhipu AI API: UNEXPECTED ERROR")
        logger.error(f"   {str(e)}")
        return False


def test_language_detection():
    """Test language detection library"""
    
    logger.info("\n🌐 Testing language detection...")
    
    try:
        from langdetect import detect
        
        test_texts = {
            'en': 'This is a test for English language detection',
            'zh': '这是一个中文语言检测测试',
            'ja': 'これは日本語の言語検出テストです',
            'es': 'Esta es una prueba de detección de idioma español'
        }
        
        for expected_lang, text in test_texts.items():
            detected = detect(text)
            if detected == expected_lang or detected.startswith(expected_lang):
                logger.info(f"  ✓ Detected '{expected_lang}' correctly")
            else:
                logger.warning(f"  ⚠ Expected '{expected_lang}', got '{detected}'")
        
        logger.info("\n✅ Language detection: WORKING")
        return True
        
    except ImportError:
        logger.error("\n❌ Language detection: langdetect library not installed")
        logger.error("   Install with: pip install langdetect")
        return False
        
    except Exception as e:
        logger.error(f"\n❌ Language detection: ERROR")
        logger.error(f"   {str(e)}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Test API connectivity')
    parser.add_argument('--youtube-key', help='YouTube Data API v3 key')
    parser.add_argument('--ai-provider', choices=['deepseek', 'zhipu'], help='AI provider to test')
    parser.add_argument('--ai-key', help='AI API key')
    parser.add_argument('--all', action='store_true', help='Test all APIs (requires all keys)')
    
    args = parser.parse_args()
    
    results = {}
    
    # Test YouTube API
    if args.youtube_key:
        results['youtube'] = test_youtube_api(args.youtube_key)
    elif args.all:
        logger.warning("⚠ Skipping YouTube API test (no key provided)")
    
    # Test AI API
    if args.ai_provider and args.ai_key:
        if args.ai_provider == 'deepseek':
            results['ai'] = test_deepseek_api(args.ai_key)
        elif args.ai_provider == 'zhipu':
            results['ai'] = test_zhipu_api(args.ai_key)
    elif args.all:
        logger.warning("⚠ Skipping AI API test (no provider/key provided)")
    
    # Test language detection (always)
    results['language_detection'] = test_language_detection()
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("TEST SUMMARY")
    logger.info("="*60)
    
    for service, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{service.upper()}: {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        logger.info("\n🎉 All tests passed! System is ready to use.")
        sys.exit(0)
    else:
        logger.info("\n⚠️  Some tests failed. Please check errors above.")
        sys.exit(1)


if __name__ == '__main__':
    main()
