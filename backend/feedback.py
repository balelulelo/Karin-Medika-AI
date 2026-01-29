"""
Feedback Tracking Module for Karin Backend

Tracks user feedback (likes, dislikes, neutrals) and calculates
accuracy/satisfaction scores for bot responses.
"""

# In-memory storage for feedback data
feedback_data = {
    "likes": 0,
    "dislikes": 0,
    "neutrals": 0,
    "total_questions": 0
}


def update_feedback(rating):
    """
    Update feedback counts based on user rating.
    
    Args:
        rating (str): Feedback type - "like", "dislike", or "neutral"
    
    Returns:
        dict: Updated feedback data
    """
    global feedback_data
    
    # Normalize rating to lowercase
    rating = rating.lower().strip()
    
    # Validate rating
    if rating not in ["like", "dislike", "neutral"]:
        raise ValueError(f"Invalid rating: {rating}. Must be 'like', 'dislike', or 'neutral'")
    
    # Update the appropriate counter
    if rating == "like":
        feedback_data["likes"] += 1
    elif rating == "dislike":
        feedback_data["dislikes"] += 1
    elif rating == "neutral":
        feedback_data["neutrals"] += 1
    
    # Always increment total questions when feedback is received
    feedback_data["total_questions"] += 1
    
    return feedback_data.copy()


def increment_question():
    """
    Increment total questions count when a question is asked
    (without requiring feedback).
    
    Returns:
        dict: Updated feedback data
    """
    global feedback_data
    feedback_data["total_questions"] += 1
    return feedback_data.copy()


def calculate_accuracy():
    """
    Calculate accuracy based on user feedback.
    
    Accuracy = (likes / (likes + dislikes)) * 100
    This represents the percentage of users who found the response helpful.
    
    Returns:
        float: Accuracy percentage (0.0 to 100.0)
    """
    total_ratings = feedback_data["likes"] + feedback_data["dislikes"]
    
    if total_ratings == 0:
        return 0.0
    
    accuracy = (feedback_data["likes"] / total_ratings) * 100
    return round(accuracy, 2)


def calculate_satisfaction_rate():
    """
    Calculate overall satisfaction rate.
    
    Satisfaction Rate = (likes / total_questions) * 100
    This represents the percentage of all questions that received positive feedback.
    
    Returns:
        float: Satisfaction rate percentage (0.0 to 100.0)
    """
    total_questions = feedback_data["total_questions"]
    
    if total_questions == 0:
        return 0.0
    
    satisfaction = (feedback_data["likes"] / total_questions) * 100
    return round(satisfaction, 2)


def get_feedback_stats():
    """
    Get complete feedback statistics including counts and accuracy metrics.
    
    Returns:
        dict: Feedback statistics including:
            - likes: Number of positive ratings
            - dislikes: Number of negative ratings
            - neutrals: Number of neutral/no feedback ratings
            - total_questions: Total questions asked
            - accuracy: Accuracy percentage (likes / rated)
            - satisfaction_rate: Overall satisfaction percentage
    """
    return {
        "likes": feedback_data["likes"],
        "dislikes": feedback_data["dislikes"],
        "neutrals": feedback_data["neutrals"],
        "total_questions": feedback_data["total_questions"],
        "accuracy": calculate_accuracy(),
        "satisfaction_rate": calculate_satisfaction_rate()
    }


def reset_feedback():
    """
    Reset all feedback data to zero.
    Useful for testing or starting fresh.
    
    Returns:
        dict: Reset feedback data
    """
    global feedback_data
    feedback_data = {
        "likes": 0,
        "dislikes": 0,
        "neutrals": 0,
        "total_questions": 0
    }
    return feedback_data.copy()
