# DB Connection Pool Exhaustion Runbook

## Category
DATABASE

## Symptoms
- Increased API latency
- SQLTransientConnectionException
- HikariPool connection timeout
- Threads waiting for database connections
- Payment or order APIs timing out

## Common Causes
- Connection pool size too small
- Database max connections reached
- Slow queries holding connections
- Connection leak
- Recent configuration change reducing pool size

## Diagnosis Steps
1. Check Hikari active connection count.
2. Check Hikari idle connection count.
3. Check database max connection usage.
4. Check slow query logs during the incident window.
5. Check recent pool-size configuration changes.

## Resolution Steps
1. Increase connection pool size only after checking database capacity.
2. Restart affected pods if connection leak is confirmed.
3. Roll back recent configuration change if issue started after deployment.
4. Tune slow queries if connections are held too long.

## Cautions
- Do not blindly increase pool size without checking database max connections.
- Do not restart all pods at once.
