# External API Timeout Runbook

## Category
DOWNSTREAM_SERVICE

## Symptoms
- HTTP read timeout
- Connection refused
- 503 from downstream service
- Increased latency in API calls

## Common Causes
- Downstream service unavailable
- Network issue
- Timeout setting too low
- Rate limiting
- Dependency saturation

## Diagnosis Steps
1. Check downstream service health.
2. Check response time from dependency.
3. Check timeout and retry configuration.
4. Check rate limiting or throttling errors.
5. Check network connectivity.

## Resolution Steps
1. Increase timeout only after confirming expected latency.
2. Reduce retry storm using backoff.
3. Fail fast or use circuit breaker.
4. Escalate to downstream owner if service is unhealthy.
