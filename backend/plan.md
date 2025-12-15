# Updated Metrics Plan

This document outlines the updated metrics collection and reporting system for the Karin Medika AI project, now including quantified database and LLM interactions, and frontend visualizations.

## Current Metrics

We collect the following metrics:

### 1. API Usage Metrics

- **`total_requests`**: Total number of requests to the `/chat` endpoint.
- **`requests_per_minute`**: Current requests per minute.
- **`average_response_time`**: Average response time for requests.

### 2. Database Interaction Metrics

- **`database_queries_attempted`**: Number of database queries attempted.
- **`database_queries_successful`**: Number of successful database queries.
- **`Database interactions (Counting Source : Database)`**: Count of unique drugs found in database.

### 3. LLM Interaction Metrics

- **`llm_calls_attempted`**: Number of LLM calls attempted.
- **`llm_calls_successful`**: Number of successful LLM calls.
- **`Gemini Interactions (Counting Source Brand Analysis and General Knowledge)`**: Count of successful brand analyses via LLM.

## Metrics Flow and How It Works

1. **Request Initiation**: When a user sends a message to the `/chat` endpoint, `get_karin_response` is called.

2. **Context Building**: `build_database_context` processes the user message:
   - Extracts drugs from the message using Gemini.
   - Searches the database for found drugs (attempted query).
   - If drugs are found, increments successful queries and unique drug count.
   - For missing drugs, attempts to get ingredients from Gemini (attempted LLM call).
   - If ingredients are found, increments successful LLM calls and brand analysis count.

3. **Metrics Update**: After processing, `update_metrics` is called with response time and the counts from the context building.

4. **Storage**: Metrics are stored in-memory in a dictionary and updated cumulatively.

5. **Retrieval**: The `/metrics` endpoint returns the current metrics dictionary.

6. **Frontend Display**: The frontend fetches metrics and displays them in a table with a close button.

This flow ensures quantified tracking of database verifications (attempted vs successful queries) and LLM interactions (attempted vs successful calls), providing insights into system performance and usage.

## Frontend Visualizations Plan

1. **Close Button**: Add an "x" button in the top-right corner of the metrics container to close it.

2. **Chart Visualization**: Add a bar chart using HTML5 Canvas to visualize the numeric metrics.

3. **Flowchart Visualization**: Add a simple text-based flowchart showing the drug analysis process.

## Implementation Status

- Backend metrics updated and tested.
- Frontend needs close button, chart, and flowchart added.
- Switch to Code mode to implement frontend changes.

## Next Steps

1. Add close button to metrics container.
2. Implement bar chart for metrics data.
3. Add process flowchart.
4. Test frontend functionality.