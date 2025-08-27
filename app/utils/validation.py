import re
from typing import List, Optional, Dict, Any


def validate_phone_number(phone: str) -> bool:
    """Validate phone number format"""
    if not phone:
        return True  # Phone is optional
    
    # Simple regex for international phone numbers
    pattern = r'^\+?[\d\s\-\(\)]{10,15}$'
    return re.match(pattern, phone.strip()) is not None


def validate_experience_years(years: int) -> bool:
    """Validate experience years"""
    return 0 <= years <= 50


def validate_technologies_list(technologies: List[str]) -> bool:
    """Validate technologies list"""
    if not technologies:
        return True

    # Check each technology name
    for tech in technologies:
        if not tech.strip():
            return False
        if len(tech.strip()) > 50:  # Max 50 chars per technology
            return False
    
    return len(technologies) <= 20  # Max 20 technologies


def validate_job_requirements(job_data: Dict[str, Any]) -> List[str]:
    """Validate job requirements and return list of errors"""
    errors = []
    
    # Required fields
    required_fields = ['title', 'description']
    for field in required_fields:
        if not job_data.get(field, '').strip():
            errors.append(f"{field} is required")
    
    # Title length
    if job_data.get('title') and len(job_data['title']) > 255:
        errors.append("Title must be less than 255 characters")
    
    # Description length
    if job_data.get('description') and len(job_data['description']) < 50:
        errors.append("Description must be at least 50 characters")
    
    # Salary validation
    salary_min = job_data.get('salary_range_min')
    salary_max = job_data.get('salary_range_max')
    
    if salary_min and salary_max:
        if salary_min > salary_max:
            errors.append("Minimum salary cannot be greater than maximum salary")
    
    if salary_min and salary_min < 0:
        errors.append("Salary cannot be negative")
    
    # Positions validation
    positions = job_data.get('positions_available', 1)
    if positions < 1:
        errors.append("At least 1 position must be available")
    
    return errors


def validate_interview_feedback(feedback_data: Dict[str, Any]) -> List[str]:
    """Validate interview feedback data"""
    errors = []
    
    # Score validation
    score_fields = ['technical_score', 'communication_score', 'problem_solving_score', 'overall_score']
    for field in score_fields:
        score = feedback_data.get(field)
        if score is not None:
            if not isinstance(score, (int, float)):
                errors.append(f"{field} must be a number")
            elif score < 0 or score > 10:
                errors.append(f"{field} must be between 0 and 10")
    
    # Recommendation validation
    recommendation = feedback_data.get('recommendation')
    if recommendation:
        valid_recommendations = ['select', 'reject', 'next_round', 'on_hold']
        if recommendation not in valid_recommendations:
            errors.append(f"Recommendation must be one of: {', '.join(valid_recommendations)}")
    
    # Hire recommendation validation
    hire_rec = feedback_data.get('hire_recommendation')
    if hire_rec:
        valid_hire_recs = ['strong_yes', 'yes', 'no', 'strong_no']
        if hire_rec not in valid_hire_recs:
            errors.append(f"Hire recommendation must be one of: {', '.join(valid_hire_recs)}")
    
    return errors


def sanitize_text_input(text: str, max_length: Optional[int] = None) -> str:
    """Sanitize text input by removing harmful characters"""
    if not text:
        return ""