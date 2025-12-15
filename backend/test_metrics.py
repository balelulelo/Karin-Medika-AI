import unittest
import time
from metrics import update_metrics, get_metrics

class TestMetrics(unittest.TestCase):

    def test_update_metrics(self):
        # Reset metrics before each test
        global metrics, response_times, request_timestamps
        metrics = {
            "total_requests": 0,
            "requests_per_minute": 0,
            "average_response_time": 0.0,
            "database_queries_attempted": 0,
            "database_queries_successful": 0,
            "llm_calls_attempted": 0,
            "llm_calls_successful": 0,
            "Database interactions (Counting Source : Database)": 0,
            "Gemini Interactions (Counting Source Brand Analysis and General Knowledge)": 0,
        }
        from collections import deque
        response_times = deque(maxlen=100)
        request_timestamps = deque(maxlen=60)


        # First update
        update_metrics(0.5, 1, 1, 0, 0, 1, 0)
        current_metrics = get_metrics()
        self.assertEqual(current_metrics["total_requests"], 1)
        self.assertAlmostEqual(current_metrics["average_response_time"], 0.5)
        self.assertEqual(current_metrics["database_queries_attempted"], 1)
        self.assertEqual(current_metrics["database_queries_successful"], 1)
        self.assertEqual(current_metrics["llm_calls_attempted"], 0)
        self.assertEqual(current_metrics["llm_calls_successful"], 0)
        self.assertEqual(current_metrics["Database interactions (Counting Source : Database)"], 1)
        self.assertEqual(current_metrics["Gemini Interactions (Counting Source Brand Analysis and General Knowledge)"], 0)

        # Second update
        update_metrics(1.0, 1, 0, 2, 1, 0, 1)
        current_metrics = get_metrics()
        self.assertEqual(current_metrics["total_requests"], 2)
        self.assertAlmostEqual(current_metrics["average_response_time"], 0.75)
        self.assertEqual(current_metrics["database_queries_attempted"], 2)
        self.assertEqual(current_metrics["database_queries_successful"], 1)
        self.assertEqual(current_metrics["llm_calls_attempted"], 2)
        self.assertEqual(current_metrics["llm_calls_successful"], 1)
        self.assertEqual(current_metrics["Database interactions (Counting Source : Database)"], 1)
        self.assertEqual(current_metrics["Gemini Interactions (Counting Source Brand Analysis and General Knowledge)"], 1)


if __name__ == '__main__':
    unittest.main()
