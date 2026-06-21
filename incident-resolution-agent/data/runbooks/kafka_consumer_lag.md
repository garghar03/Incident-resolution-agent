# Kafka Consumer Lag Runbook

## Category
KAFKA

## Symptoms
- Consumer lag increasing
- Delayed event processing
- Rebalancing messages
- Processing throughput reduced

## Common Causes
- Slow consumer processing
- Broker instability
- Too few consumer instances
- Poison messages
- Large batch size or slow downstream dependency

## Diagnosis Steps
1. Check consumer group lag.
2. Check partition assignment.
3. Check broker health.
4. Check recent consumer deployments.
5. Check downstream dependencies used by the consumer.

## Resolution Steps
1. Scale consumers if partitions allow it.
2. Pause or isolate poison messages.
3. Tune batch size and poll settings.
4. Fix slow downstream dependency.
