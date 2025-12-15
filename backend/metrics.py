import time
from collections import deque

# In-memory storage for metrics
metrics = {
    "total_requests": 0,
    "requests_per_minute": 0,
    "average_response_time": 0.0,
    "database_queries_attempted": 0,
    "database_queries_successful": 0,
    "llm_calls_attempted": 0,
    "llm_calls_successful": 0,
    "Database interactions": 0,
    "Gemini Interactions": 0,
}

# A deque to store response times for calculating the average
response_times = deque(maxlen=100) # Store the last 100 response times

# A deque to store request timestamps for calculating requests per minute
request_timestamps = deque(maxlen=60)


def update_metrics(response_time, db_attempted, db_successful, llm_attempted, llm_successful, db_interactions, llm_interactions):
    """Update all metrics."""
    global metrics

    metrics["total_requests"] += 1

    # Update response time
    response_times.append(response_time)
    metrics["average_response_time"] = sum(response_times) / len(response_times)

    # Update requests per minute
    current_time = time.time()
    request_timestamps.append(current_time)
    # Remove timestamps older than 60 seconds
    while request_timestamps and request_timestamps[0] < current_time - 60:
        request_timestamps.popleft()
    metrics["requests_per_minute"] = len(request_timestamps)

    metrics["database_queries_attempted"] += db_attempted
    metrics["database_queries_successful"] += db_successful
    metrics["llm_calls_attempted"] += llm_attempted
    metrics["llm_calls_successful"] += llm_successful
    metrics["Database interactions"] += db_interactions
    metrics["Gemini Interactions"] += llm_interactions

def get_metrics():
    """Return the current metrics."""
    return metrics
