from typing import Dict, Any
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.interview import Interview


def create_interview_invitation_template(
    candidate: Candidate,
    interview: Interview,
    job: Job
) -> Dict[str, str]:
    """Create interview invitation email template"""
    subject = f"Interview Invitation - {job.title} Position"

    body = f"""
Dear {candidate.name},

Thank you for your interest in the {job.title} position at our company.

We are pleased to inform you that your profile has been shortlisted, and we would like to invite you for an interview.

Interview Details:
- Position: {job.title}
- Date & Time: {interview.scheduled_time.strftime('%A, %B %d, %Y at %I:%M %p') if interview.scheduled_time else 'TBD'}
- Duration: {interview.duration_minutes} minutes
- Type: {interview.interview_type.replace('_', ' ').title()}
- Meeting Link: {interview.meeting_link or 'Will be shared separately'}

What to Expect:
This will be a {interview.interview_type.replace('_', ' ')} focusing on your technical expertise and experience with {', '.join(job.technologies_required[:3]) if job.technologies_required else 'relevant technologies'}.

Please prepare to:
- Discuss your past projects and achievements
- Demonstrate your problem-solving approach
- Share your understanding of the technologies mentioned in the job description

Please confirm your attendance by replying to this email at least 24 hours before the interview. If you need to reschedule, please let us know as soon as possible.

We look forward to meeting you!

Best regards,
HR Team
    """.strip()

    return {"subject": subject, "body": body}


def create_rejection_email_template(candidate: Candidate, job: Job) -> Dict[str, str]:
    """Create rejection email template"""
    subject = f"Application Update - {job.title} Position"

    body = f"""
Dear {candidate.name},

Thank you for your interest in the {job.title} position at our company and for taking the time to share your application with us.

After careful consideration of your qualifications and experience, we have decided to move forward with other candidates whose background more closely matches our current requirements.

This decision was not made lightly, as we received many qualified applications. We were impressed by your background and encourage you to apply for future opportunities that may be a better fit for your skills and career goals.

We will keep your resume on file for future consideration and may reach out if a suitable position becomes available.

Thank you again for your interest in our company, and we wish you success in your job search.

Best regards,
HR Team
    """.strip()

    return {"subject": subject, "body": body}


def create_interviewer_notification_template(
    candidate: Candidate,
    interview: Interview,
    job: Job
) -> Dict[str, str]:
    """Create interviewer notification email template"""
    subject = f"Interview Scheduled - {candidate.name} for {job.title}"

    body = f"""
Dear Interviewer,

You have been assigned to conduct an interview for the {job.title} position.

Candidate Information:
- Name: {candidate.name}
- Email: {candidate.email}
- Experience: {candidate.experience_years} years
- Technologies: {', '.join(candidate.technologies) if candidate.technologies else 'Not specified'}
- Current Stage: {candidate.current_stage.replace('_', ' ').title()}

Interview Details:
- Date & Time: {interview.scheduled_time.strftime('%A, %B %d, %Y at %I:%M %p') if interview.scheduled_time else 'TBD'}
- Duration: {interview.duration_minutes} minutes
- Type: {interview.interview_type.replace('_', ' ').title()}
- Meeting Link: {interview.meeting_link or 'Please create meeting link'}

Candidate Scores:
- Overall Score: {candidate.overall_score}/10
- Technical Score: {candidate.technical_score}/10
- Match Percentage: {candidate.match_percentage}%

Please review the candidate's resume (attached) before the interview and prepare relevant technical questions based on the job requirements.

After the interview, please submit your feedback through the system within 24 hours.

If you have any questions or need to reschedule, please contact HR immediately.

Thank you for your time!

Best regards,
HR Team
    """.strip()

    return {"subject": subject, "body": body}


def create_interview_reminder_template(
    candidate: Candidate,
    interview: Interview,
    job: Job,
    hours_before: int = 24
) -> Dict[str, str]:
    """Create interview reminder email template"""
    subject = f"Interview Reminder - {job.title} - Tomorrow at {interview.scheduled_time.strftime('%I:%M %p') if interview.scheduled_time else 'TBD'}"
    
    if hours_before == 1:
        subject = f"Interview in 1 Hour - {job.title}"
        time_text = "in 1 hour"
    else:
        time_text = f"in {hours_before} hours"
    
    body = f"""
Dear {candidate.name},

This is a friendly reminder about your upcoming interview {time_text}.

Interview Details:
- Position: {job.title}
- Date & Time: {interview.scheduled_time.strftime('%A, %B %d, %Y at %I:%M %p') if interview.scheduled_time else 'TBD'}
- Duration: {interview.duration_minutes} minutes
- Meeting Link: {interview.meeting_link or 'Check previous email for meeting details'}

Pre-Interview Checklist:
□ Review the job description and requirements
□ Prepare examples of your relevant work experience
□ Test your internet connection and audio/video setup
□ Have a copy of your resume handy
□ Prepare questions about the role and company

Please join the meeting 5 minutes before the scheduled time and send a confirmation once you're ready.

If you have any last-minute questions or technical issues, please contact us immediately.

Good luck with your interview!

Best regards,
HR Team
    """.strip()
    
    return {"subject": subject, "body": body}


def create_hr_summary_email_template(
    workflow_summary: Dict[str, Any]
) -> Dict[str, str]:
    """Create HR summary email template"""
    subject = f"Hiring Workflow Summary - {workflow_summary.get('job_title', 'Unknown Position')}"

    candidates_summary = ""
    for candidate in workflow_summary.get('candidates', []):
        candidates_summary += f"""
- {candidate['name']} ({candidate['email']})
  Stage: {candidate['stage'].replace('_', ' ').title()}
  Score: {candidate.get('overall_score', 0)}/10
  Match: {candidate.get('match_percentage', 0)}%
  Recommendation: {candidate.get('recommendation', 'N/A')}
"""

    body = f"""
Dear HR Team,

Here is the summary of the automated hiring workflow for {workflow_summary.get('job_title', 'Unknown Position')}.

Workflow Status: {workflow_summary.get('status', 'Unknown')}
Total Candidates Processed: {len(workflow_summary.get('candidates', []))}

Candidate Summary:
{candidates_summary}

Interviews Scheduled: {workflow_summary.get('interviews_scheduled', 0)}
Emails Sent: {workflow_summary.get('emails_sent', 0)}

Pending Actions:
{chr(10).join(f"- {action}" for action in workflow_summary.get('pending_actions', []))}

Performance Metrics:
- Total Processing Time: {workflow_summary.get('total_time', 'N/A')}
- Success Rate: {workflow_summary.get('success_rate', 'N/A')}%
- Agent Utilization: {workflow_summary.get('agent_stats', {})}

Please review the results and take any necessary manual actions for candidates requiring human intervention.

Best regards,
Automated Hiring System
    """.strip()
    
    return {"subject": subject, "body": body}
