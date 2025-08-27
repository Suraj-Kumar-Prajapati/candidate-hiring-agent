## Repo Description

Teams Hiring Agent is a lightweight automation bot that integrates directly with Microsoft Teams to streamline the hiring workflow. Traditionally, HR teams manually share resumes, tag technical leads, coordinate interview availability, schedule meetings, and send reminders — all of which is time-consuming and error-prone. This project provides a single, focused AI-assisted agent that automates those steps, keeping the workflow inside Teams without requiring an external platform.

## The agent listens for new resumes posted in a Teams channel via Microsoft Graph change notifications. It then:
- Parses candidate details (name, experience, availability) using a simple resume parser.
- Identifies an appropriate interviewer from a configurable pool.
- Schedules a Teams meeting (via Microsoft Graph OnlineMeetings API).
- Posts details back into the Teams thread, ensuring transparency for HR and technical leads.
- Optionally triggers reminders for candidates and interviewers before the meeting.

The implementation is intentionally minimal — no unnecessary APIs, WebSockets, or multi-agent complexity.
This repo is for HR teams or organizations seeking to simplify hiring inside Teams with minimal setup and maximum clarity.
