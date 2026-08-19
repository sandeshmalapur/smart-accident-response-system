"""
Static welfare check strings per project safety specification.

CRITICAL SAFETY CONSTRAINT:
This module contains 100% FIXED, pre-written strings reviewed once for safety.
These strings are NEVER dynamically generated, template-formatted, or composed
by AI models based on incident severity or injury guesses.
"""

WELFARE_CHECK_PROMPT = "We detected a possible accident. Are you able to respond?"

SAFETY_GUIDANCE = (
    "Stay as still as possible. Do not attempt to move unless there is immediate danger (fire, traffic). "
    "Help is on the way."
)

ESCALATION_NOTICE = "No response received. Emergency responders have been notified with elevated priority."
