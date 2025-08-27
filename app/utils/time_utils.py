from datetime import datetime, timedelta
from typing import List
import pytz


def parse_time_availability(availability_text: str) -> List[str]:
    """Parse human-readable time availability into structured format"""
    availability_patterns = {
        'flexible': ['weekdays 9-17', 'weekends 10-16'],
        'weekdays': ['monday-friday 9-17'],
        'mornings': ['weekdays 9-12'],
        'afternoons': ['weekdays 13-17'],
        'evenings': ['weekdays 18-20']
    }
    
    availability_lower = availability_text.lower()
    
    for pattern, times in availability_patterns.items():
        if pattern in availability_lower:
            return times
    
    # Try to extract specific times
    if 'am' in availability_lower or 'pm' in availability_lower:
        return [availability_text]
    
    return ['weekdays 9-17']  # default


def find_common_availability(
    candidate_availability: str,
    interviewer_slots: List[str]
) -> List[datetime]:
    """Find common availability between candidate and interviewer"""
    candidate_times = parse_time_availability(candidate_availability)
    
    # This is a simplified implementation
    # In practice, you'd need more sophisticated time parsing
    common_slots = []
    
    base_date = datetime.now().date() + timedelta(days=1)  # Start from tomorrow
    
    for i in range(7):  # Check next 7 days
        check_date = base_date + timedelta(days=i)
        
        # Skip weekends for now (can be made configurable)
        if check_date.weekday() >= 5:
            continue
        
        # Create time slots for this day
        for hour in range(9, 17):  # 9 AM to 5 PM
            slot_time = datetime.combine(check_date, datetime.min.time().replace(hour=hour))
            common_slots.append(slot_time)
    
    return common_slots[:5]  # Return first 5 available slots


def format_interview_time(interview_time: datetime, timezone: str = "UTC") -> str:
    """Format interview time for display"""
    if timezone != "UTC":
        tz = pytz.timezone(timezone)
        interview_time = interview_time.astimezone(tz)
    
    return interview_time.strftime("%A, %B %d, %Y at %I:%M %p %Z")


def get_business_hours_slots(
    start_date: datetime,
    end_date: datetime,
    duration_minutes: int = 60,
    timezone: str = "UTC"
) -> List[datetime]:
    """Get available business hour slots between two dates"""
    slots = []
    current_date = start_date.date()
    
    while current_date <= end_date.date():
        # Skip weekends
        if current_date.weekday() < 5:  # Monday = 0, Friday = 4
            # Create slots from 9 AM to 5 PM
            for hour in range(9, 17):
                slot_time = datetime.combine(current_date, datetime.min.time().replace(hour=hour))
                if timezone != "UTC":
                    tz = pytz.timezone(timezone)
                    slot_time = tz.localize(slot_time)
                slots.append(slot_time)
        
        current_date += timedelta(days=1)
    
    return slots


def calculate_interview_duration(interview_type: str) -> int:
    """Calculate interview duration based on type"""
    duration_map = {
        "technical_round_1": 60,
        "technical_round_2": 90,
        "hr_round": 30,
        "managerial_round": 45,
        "final_round": 60,
        "panel_interview": 90
    }
    
    return duration_map.get(interview_type, 60)
