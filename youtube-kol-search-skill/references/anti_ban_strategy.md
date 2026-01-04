# Anti-Ban Strategy

Comprehensive protection mechanisms to prevent API rate limiting and account suspension.

## Overview

YouTube and AI APIs have strict rate limits. This system implements 5 layers of protection to ensure reliable operation without triggering bans or suspensions.

## Layer 1: API Key Rotation

### Strategy

**Never rely on a single API key**. Distribute load across multiple keys to stay under quota limits.

### Implementation

```python
class APIKeyManager:
    def __init__(self, db):
        self.db = db
        self.current_index = 0
        self.failed_keys = set()
        
    def get_next_available_key(self) -> Optional[str]:
        """Get next API key with available quota"""
        
        # Get all active keys sorted by usage
        keys = self.db.query(APIKey).filter(
            APIKey.is_active == True,
            APIKey.api_type == 'youtube',
            APIKey.id.notin_(self.failed_keys)
        ).order_by(
            APIKey.priority.desc(),
            APIKey.used_quota.asc()
        ).all()
        
        if not keys:
            raise NoAvailableKeysException("All API keys exhausted")
        
        for key in keys:
            # Check if needs daily reset
            if key.last_reset_date < date.today():
                key.used_quota = 0
                key.last_reset_date = date.today()
                self.db.commit()
            
            # Check if has quota remaining
            remaining = key.daily_quota - key.used_quota
            if remaining >= 100:  # Minimum for one search
                return key.api_key
        
        raise QuotaExhaustedException("All keys at quota limit")
    
    def mark_key_failed(self, api_key: str, reason: str):
        """Temporarily disable a key"""
        self.failed_keys.add(api_key)
        
        # Log the failure
        self.db.execute(
            "INSERT INTO api_key_failures (api_key, reason, failed_at) "
            "VALUES (:key, :reason, NOW())",
            {"key": api_key, "reason": reason}
        )
        
        # Auto-recover after cooldown period
        if reason == 'rate_limit':
            cooldown = 3600  # 1 hour
        elif reason == 'quota_exceeded':
            cooldown = 86400  # 24 hours
        else:
            cooldown = 300  # 5 minutes
        
        # Schedule re-enablement
        self.schedule_key_recovery(api_key, cooldown)
    
    def record_usage(self, api_key: str, units: int):
        """Track quota consumption"""
        self.db.execute(
            "UPDATE api_keys SET used_quota = used_quota + :units "
            "WHERE api_key = :key",
            {"units": units, "key": api_key}
        )
        self.db.commit()
```

### Best Practices

1. **Minimum 3 keys recommended** for production
2. **Rotate keys proactively** - switch before quota exhaustion
3. **Monitor usage patterns** - identify high-consumption operations
4. **Stagger key resets** - use keys from different Google Cloud projects with different billing cycles

### Quota Allocation

**YouTube Data API v3 Quotas**:

| Operation | Cost | Notes |
|-----------|------|-------|
| search.list | 100 | Most expensive operation |
| channels.list | 1 | Cheap, can batch 50 IDs |
| playlistItems.list | 1 | Per request |
| videos.list | 1 | Can batch 50 IDs |

**Example Calculation**:
- 1 keyword search with 500 results:
  - Search: 10 pages × 100 = 1,000 units
  - Channels: 500/50 = 10 calls × 1 = 10 units
  - Playlists: 500 × 1 = 500 units
  - Videos: 500 × 1 = 500 units
  - **Total: ~2,010 units**

With 10,000 daily quota, you can search ~5 keywords/day per key.

## Layer 2: Request Throttling

### Dynamic Delay Calculation

```python
class RequestThrottler:
    def __init__(self, mode: str = 'normal'):
        self.mode = mode
        self.last_request_time = None
        self.request_count = 0
        self.window_start = time.time()
        
    async def throttle(self):
        """Enforce rate limiting with jitter"""
        
        # Calculate delay based on mode
        if self.mode == 'normal':
            base_delay = random.uniform(0.5, 1.0)
        elif self.mode == 'accelerated':
            base_delay = random.uniform(0.2, 0.3)
        else:
            base_delay = 0.5
        
        # Add jitter to prevent thundering herd
        jitter = random.uniform(-0.1, 0.1)
        delay = max(0.1, base_delay + jitter)
        
        # Enforce minimum time between requests
        if self.last_request_time:
            elapsed = time.time() - self.last_request_time
            if elapsed < delay:
                await asyncio.sleep(delay - elapsed)
        
        # Update tracking
        self.last_request_time = time.time()
        self.request_count += 1
        
        # Log for monitoring
        logger.debug(f"Throttled request (delay={delay:.2f}s, total={self.request_count})")
    
    def should_pause(self) -> bool:
        """Check if we should take a longer pause"""
        
        # Take a break every 100 requests
        if self.request_count % 100 == 0:
            return True
        
        # Check sustained high rate
        window_duration = time.time() - self.window_start
        if window_duration < 60 and self.request_count > 80:
            return True
        
        return False
    
    async def long_pause(self):
        """Extended pause to reset rate limits"""
        pause_duration = random.uniform(10, 20)
        logger.info(f"Taking long pause ({pause_duration:.1f}s)")
        await asyncio.sleep(pause_duration)
        
        # Reset window
        self.request_count = 0
        self.window_start = time.time()
```

### Adaptive Throttling

```python
class AdaptiveThrottler(RequestThrottler):
    def __init__(self):
        super().__init__()
        self.error_count = 0
        self.success_count = 0
        
    async def throttle(self):
        """Adjust delay based on error rate"""
        
        # Calculate error rate
        total_requests = self.error_count + self.success_count
        if total_requests > 10:
            error_rate = self.error_count / total_requests
            
            if error_rate > 0.1:  # >10% errors
                # Slow down significantly
                delay = random.uniform(2.0, 3.0)
                logger.warning(f"High error rate ({error_rate:.1%}), increasing delay")
            elif error_rate > 0.05:  # >5% errors
                # Moderate slowdown
                delay = random.uniform(1.0, 1.5)
            else:
                # Normal operation
                delay = random.uniform(0.5, 1.0)
        else:
            delay = random.uniform(0.5, 1.0)
        
        await asyncio.sleep(delay)
    
    def record_success(self):
        self.success_count += 1
    
    def record_error(self):
        self.error_count += 1
```

## Layer 3: Rate Limiting

### Per-Key Rate Limits

```python
class PerKeyRateLimiter:
    def __init__(self, max_rpm: int = 60):
        self.max_rpm = max_rpm
        self.windows = {}  # {api_key: deque of timestamps}
        
    def check_rate_limit(self, api_key: str) -> bool:
        """Check if API key is within rate limit"""
        
        now = time.time()
        minute_ago = now - 60
        
        # Initialize window if not exists
        if api_key not in self.windows:
            self.windows[api_key] = deque()
        
        window = self.windows[api_key]
        
        # Remove old timestamps
        while window and window[0] < minute_ago:
            window.popleft()
        
        # Check if under limit
        if len(window) >= self.max_rpm:
            # Calculate wait time
            oldest_request = window[0]
            wait_time = 60 - (now - oldest_request)
            raise RateLimitException(
                f"Rate limit exceeded. Wait {wait_time:.1f}s",
                wait_time=wait_time
            )
        
        # Record this request
        window.append(now)
        return True
    
    def get_current_rate(self, api_key: str) -> int:
        """Get current requests per minute"""
        if api_key not in self.windows:
            return 0
        
        now = time.time()
        minute_ago = now - 60
        
        window = self.windows[api_key]
        return sum(1 for ts in window if ts >= minute_ago)
```

### Global Rate Limiter

```python
class GlobalRateLimiter:
    """Limit total API calls across all keys"""
    
    def __init__(self, max_calls_per_minute: int = 300):
        self.max_calls = max_calls_per_minute
        self.call_history = deque()
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        """Wait until we can make another call"""
        async with self.lock:
            now = time.time()
            minute_ago = now - 60
            
            # Clean old entries
            while self.call_history and self.call_history[0] < minute_ago:
                self.call_history.popleft()
            
            # Check if at limit
            if len(self.call_history) >= self.max_calls:
                # Wait until oldest call expires
                wait_time = 60 - (now - self.call_history[0])
                logger.warning(f"Global rate limit reached. Waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
                
                # Retry acquire
                return await self.acquire()
            
            # Record this call
            self.call_history.append(now)
```

## Layer 4: Error Handling

### HTTP Error Detection

```python
class APIErrorHandler:
    def __init__(self, api_key_manager):
        self.api_key_manager = api_key_manager
        self.error_counts = defaultdict(int)
        
    async def handle_api_call(self, api_key: str, api_func, *args, **kwargs):
        """Wrap API call with error handling"""
        
        try:
            result = await api_func(*args, **kwargs)
            
            # Reset error count on success
            if api_key in self.error_counts:
                self.error_counts[api_key] = 0
            
            return result
            
        except HttpError as e:
            status_code = e.resp.status
            
            if status_code == 403:
                # Quota exceeded or banned
                reason = self._parse_error_reason(e)
                
                if 'quotaExceeded' in reason:
                    logger.warning(f"Quota exceeded for key {api_key[:8]}...")
                    self.api_key_manager.mark_key_failed(api_key, 'quota_exceeded')
                    
                    # Try with different key
                    new_key = self.api_key_manager.get_next_available_key()
                    return await self.handle_api_call(new_key, api_func, *args, **kwargs)
                
                elif 'forbidden' in reason.lower():
                    logger.error(f"Key {api_key[:8]}... may be banned!")
                    self.api_key_manager.mark_key_failed(api_key, 'banned')
                    
                    # Pause entire system briefly
                    await asyncio.sleep(60)
                    
                    # Try with different key
                    new_key = self.api_key_manager.get_next_available_key()
                    return await self.handle_api_call(new_key, api_func, *args, **kwargs)
            
            elif status_code == 429:
                # Too many requests - rate limited
                logger.warning(f"Rate limited on key {api_key[:8]}...")
                
                # Exponential backoff
                backoff_time = 2 ** self.error_counts[api_key]
                backoff_time = min(backoff_time, 300)  # Max 5 minutes
                
                logger.info(f"Backing off for {backoff_time}s")
                await asyncio.sleep(backoff_time)
                
                self.error_counts[api_key] += 1
                
                # Retry with same key after backoff
                return await self.handle_api_call(api_key, api_func, *args, **kwargs)
            
            elif status_code == 500 or status_code >= 502:
                # Server error - transient, retry with backoff
                backoff_time = random.uniform(1, 3)
                await asyncio.sleep(backoff_time)
                
                return await self.handle_api_call(api_key, api_func, *args, **kwargs)
            
            else:
                # Unknown error
                logger.error(f"Unexpected error {status_code}: {e}")
                raise
        
        except Exception as e:
            logger.error(f"Non-HTTP error: {e}")
            raise
    
    def _parse_error_reason(self, error: HttpError) -> str:
        """Extract error reason from response"""
        try:
            error_details = json.loads(error.content)
            return error_details.get('error', {}).get('message', '')
        except:
            return str(error)
```

### Circuit Breaker Pattern

```python
class CircuitBreaker:
    """Prevent cascading failures"""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
        
    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        
        if self.state == 'OPEN':
            if time.time() - self.last_failure_time > self.timeout:
                logger.info("Circuit breaker: OPEN -> HALF_OPEN")
                self.state = 'HALF_OPEN'
            else:
                raise CircuitBreakerOpenException("Too many failures, circuit is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            
            # Success - reset if in HALF_OPEN
            if self.state == 'HALF_OPEN':
                logger.info("Circuit breaker: HALF_OPEN -> CLOSED")
                self.state = 'CLOSED'
                self.failures = 0
            
            return result
            
        except Exception as e:
            self.failures += 1
            self.last_failure_time = time.time()
            
            if self.failures >= self.failure_threshold:
                logger.error(f"Circuit breaker: -> OPEN (failures={self.failures})")
                self.state = 'OPEN'
            
            raise
```

## Layer 5: Exponential Backoff

### Backoff Strategy

```python
class ExponentialBackoff:
    def __init__(self, 
                 base_delay: float = 1.0,
                 max_delay: float = 60.0,
                 max_retries: int = 5):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.max_retries = max_retries
        
    async def execute_with_backoff(self, func, *args, **kwargs):
        """Execute function with exponential backoff on failures"""
        
        for attempt in range(self.max_retries):
            try:
                result = await func(*args, **kwargs)
                return result
                
            except Exception as e:
                if attempt == self.max_retries - 1:
                    # Last attempt failed
                    logger.error(f"All {self.max_retries} attempts failed")
                    raise
                
                # Calculate backoff delay
                delay = min(
                    self.base_delay * (2 ** attempt),
                    self.max_delay
                )
                
                # Add jitter
                jitter = random.uniform(0, 0.1 * delay)
                total_delay = delay + jitter
                
                logger.warning(
                    f"Attempt {attempt + 1} failed: {e}. "
                    f"Retrying in {total_delay:.1f}s..."
                )
                
                await asyncio.sleep(total_delay)
```

### Usage Example

```python
backoff = ExponentialBackoff()

result = await backoff.execute_with_backoff(
    youtube_api.search,
    keyword="PC cleanup",
    max_results=50
)
```

## Combined Protection System

### Integration Example

```python
class ProtectedYouTubeClient:
    """YouTube client with all 5 protection layers"""
    
    def __init__(self, db):
        self.api_key_manager = APIKeyManager(db)
        self.throttler = AdaptiveThrottler()
        self.rate_limiter = PerKeyRateLimiter(max_rpm=60)
        self.global_limiter = GlobalRateLimiter(max_calls_per_minute=300)
        self.error_handler = APIErrorHandler(self.api_key_manager)
        self.circuit_breaker = CircuitBreaker()
        self.backoff = ExponentialBackoff()
        
    async def search(self, keyword: str, **params):
        """Protected search with all layers"""
        
        async def _search():
            # Layer 1: Get API key
            api_key = self.api_key_manager.get_next_available_key()
            
            # Layer 3: Check rate limits
            self.rate_limiter.check_rate_limit(api_key)
            await self.global_limiter.acquire()
            
            # Layer 2: Throttle
            await self.throttler.throttle()
            
            # Make actual API call with Layer 4 (error handling)
            youtube = build('youtube', 'v3', developerKey=api_key)
            result = await self.error_handler.handle_api_call(
                api_key,
                youtube.search().list,
                q=keyword,
                part='snippet',
                **params
            )
            
            # Record usage
            self.api_key_manager.record_usage(api_key, 100)
            self.throttler.record_success()
            
            return result
        
        # Layer 5: Exponential backoff
        # Layer 4: Circuit breaker
        return await self.backoff.execute_with_backoff(
            self.circuit_breaker.call,
            _search
        )
```

## Monitoring & Alerts

### Quota Dashboard

```python
def get_quota_status():
    """Get real-time quota status for all keys"""
    
    keys = db.query(APIKey).filter(
        APIKey.api_type == 'youtube',
        APIKey.is_active == True
    ).all()
    
    status = []
    for key in keys:
        remaining = key.daily_quota - key.used_quota
        percent_used = (key.used_quota / key.daily_quota) * 100
        
        # Determine health status
        if percent_used >= 95:
            health = 'CRITICAL'
        elif percent_used >= 80:
            health = 'WARNING'
        else:
            health = 'OK'
        
        status.append({
            'key_id': key.id,
            'display_name': key.display_name,
            'used': key.used_quota,
            'total': key.daily_quota,
            'remaining': remaining,
            'percent_used': round(percent_used, 1),
            'health': health,
            'resets_at': 'UTC midnight'
        })
    
    return status
```

### Alert System

```python
class QuotaAlertSystem:
    def __init__(self):
        self.thresholds = {
            'warning': 0.8,   # 80%
            'critical': 0.95  # 95%
        }
        self.alerted_keys = set()
    
    def check_and_alert(self, api_key_id: int):
        """Send alerts if quota threshold exceeded"""
        
        key = db.query(APIKey).get(api_key_id)
        usage_ratio = key.used_quota / key.daily_quota
        
        if usage_ratio >= self.thresholds['critical']:
            if api_key_id not in self.alerted_keys:
                self.send_alert(
                    level='CRITICAL',
                    message=f"API key {key.display_name} at {usage_ratio:.1%} quota"
                )
                self.alerted_keys.add(api_key_id)
        
        elif usage_ratio >= self.thresholds['warning']:
            if api_key_id not in self.alerted_keys:
                self.send_alert(
                    level='WARNING',
                    message=f"API key {key.display_name} at {usage_ratio:.1%} quota"
                )
                self.alerted_keys.add(api_key_id)
    
    def send_alert(self, level: str, message: str):
        """Send alert (email, Slack, etc.)"""
        logger.log(level, message)
        # TODO: Implement actual alerting (email, Slack, etc.)
```

## Best Practices Summary

### DO's ✅

1. **Use multiple API keys** (minimum 3)
2. **Implement all 5 protection layers**
3. **Monitor quota usage in real-time**
4. **Log all API calls for audit**
5. **Test with small searches first**
6. **Use normal mode by default**
7. **Rotate keys proactively, not reactively**
8. **Add random jitter to delays**
9. **Handle all HTTP error codes**
10. **Implement graceful degradation**

### DON'Ts ❌

1. **Never hardcode API keys**
2. **Don't ignore rate limit errors**
3. **Don't retry immediately without backoff**
4. **Don't use the same key for all requests**
5. **Don't exceed 100 requests/minute per key**
6. **Don't disable protection in production**
7. **Don't ignore circuit breaker state**
8. **Don't skip logging/monitoring**
9. **Don't assume errors are transient**
10. **Don't use accelerated mode with <3 keys**

## Testing the Protection System

### Stress Test

```python
async def stress_test():
    """Test system under high load"""
    
    client = ProtectedYouTubeClient(db)
    
    # Simulate rapid searches
    keywords = ["PC cleanup", "Windows optimizer", "disk cleaner"]
    
    tasks = []
    for keyword in keywords:
        for _ in range(10):  # 10 searches per keyword
            tasks.append(client.search(keyword, max_results=50))
    
    # Execute concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Analyze results
    successes = sum(1 for r in results if not isinstance(r, Exception))
    failures = len(results) - successes
    
    print(f"Success rate: {successes}/{len(results)} ({successes/len(results):.1%})")
    print(f"Quota usage: {get_total_quota_usage()}")
```

### Failure Simulation

```python
async def test_key_exhaustion():
    """Test behavior when all keys exhausted"""
    
    client = ProtectedYouTubeClient(db)
    
    # Artificially set all keys to max quota
    db.execute("UPDATE api_keys SET used_quota = daily_quota")
    
    try:
        await client.search("test keyword")
        assert False, "Should have raised QuotaExhaustedException"
    except QuotaExhaustedException:
        print("✓ Correctly handled quota exhaustion")
    
    # Test recovery after reset
    db.execute("UPDATE api_keys SET used_quota = 0")
    result = await client.search("test keyword")
    assert result is not None
    print("✓ Successfully recovered after quota reset")
```

## Emergency Procedures

### If You Get Banned

1. **Immediately stop all API calls**
2. **Review logs to identify cause**
3. **Check if ban is temporary (usually 24h) or permanent**
4. **If temporary**: Wait, then resume with stricter limits
5. **If permanent**: Contact Google Cloud support, provision new keys
6. **Update protection parameters** to prevent recurrence

### Quota Recovery Plan

```python
def emergency_quota_recovery():
    """Steps when quota exhausted"""
    
    # 1. Pause all active tasks
    pause_all_searches()
    
    # 2. Wait for UTC midnight (quota reset)
    time_until_reset = calculate_time_until_utc_midnight()
    logger.info(f"Waiting {time_until_reset} for quota reset")
    
    # 3. Meanwhile, use cached data
    serve_cached_results_only()
    
    # 4. After reset, resume with conservative limits
    set_mode('conservative')
    resume_searches()
```

This 5-layer protection system ensures reliable, long-term operation without triggering API bans or rate limits.
