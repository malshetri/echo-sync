# Lo-Fi Testing Protocol

## Purpose

The lo-fi test is designed to evaluate Echo-Sync before relying on the complete
technical implementation. A Wizard-of-Oz setup lets the team observe whether
the spoken interaction is understandable without visual hints.

## Test Setup

Three team members take part in each session:

- One person acts as the Echo-Sync system and follows prepared responses.
- One person acts as the user and completes the tasks without looking at a
  screen.
- One person observes the session and records hesitation, errors, and comments.

The observer should not help unless the user is unable to continue. After each
scenario, the user should briefly explain what they expected the system to do.

## Scenario 1: Basic Music Control

**Goal:** Check whether the direct commands are easy to discover and remember.

Tasks:

1. Start playing music.
2. Increase or decrease the volume.
3. Skip to the next track.
4. Pause and resume playback.

Points to observe:

- Whether the user knows when the system is listening.
- Whether the confirmation sounds are understood.
- Which command wording feels most natural.
- Whether spoken feedback is too long or too short.

## Scenario 2: Context-Based Request

**Goal:** Check whether users understand that they can describe their situation
instead of naming a playlist.

Tasks:

1. Say, "I am tired."
2. Listen to the system's response and selected music.
3. Say, "I need something more energetic."
4. Ask for music suitable for studying.

Points to observe:

- Whether the selected category matches the user's expectation.
- Whether the response explains the choice clearly.
- Whether users describe a mood, an activity, or a music genre first.

## Scenario 3: Help and Error Recovery

**Goal:** Check whether a user can recover without reading instructions.

Tasks:

1. Ask an unrelated question such as, "What is the weather?"
2. Stay silent when the system starts listening.
3. Give an unclear command.
4. Ask, "What can I say?"

Points to observe:

- Whether the off-topic reply is polite and understandable.
- Whether progressive help gives enough information.
- Whether the user knows how to try again.
- Whether silence handling feels helpful rather than intrusive.

## Evaluation Criteria

For each task, the observer records:

| Criterion | Measurement |
|---|---|
| Completion | Completed independently, completed with help, or not completed |
| First-attempt success | Yes or no |
| Recovery | Whether the user recovered after an error |
| Command wording | The exact phrase used by the participant |
| User feedback | Short comments made during or after the task |

## Current Status

This document records the testing method used to guide design decisions. Formal
results are not included because no complete participant dataset was retained.
The automated test plan is documented separately in
[12_test_plan.md](12_test_plan.md).
