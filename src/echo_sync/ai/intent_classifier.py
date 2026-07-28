"""
Echo-Sync AI intent classifier.

Calls the OpenAI API with the system prompt and forces structured JSON
output matching the IntentResult schema. Includes rule-based fast-path
for common direct commands before hitting the API.
"""

import json
import logging
import re
from typing import Optional

from openai import OpenAI

from echo_sync.ai.intent_schema import IntentResult
from echo_sync.config.prompts import INTENT_CLASSIFIER_SYSTEM_PROMPT
from echo_sync.config.settings import Settings

logger = logging.getLogger(__name__)


# Common controls are handled locally so they stay quick and predictable.

DIRECT_COMMAND_PATTERNS: list[tuple[re.Pattern, str, str]] = [
    # Each entry contains a pattern, an action, and the spoken reply.
    (re.compile(r"^pause$", re.IGNORECASE), "pause", "Music paused."),
    (re.compile(r"^stop(\s+music)?$", re.IGNORECASE), "stop", "Music stopped."),
    (re.compile(r"^(resume|continue|unpause)$", re.IGNORECASE), "resume", "Resuming music."),
    (re.compile(r"^next(\s+song)?$", re.IGNORECASE), "next", "Playing next song."),
    (re.compile(r"^(previous|prev)(\s+song)?$", re.IGNORECASE), "previous", "Playing previous song."),
    (re.compile(r"^(volume\s+up|louder|turn\s+it\s+up|make\s+it\s+louder)$", re.IGNORECASE), "volume_up", "Volume increased."),
    (re.compile(r"^(volume\s+down|quieter|turn\s+it\s+down|lower\s+the\s+volume|make\s+it\s+quieter)$", re.IGNORECASE), "volume_down", "Volume decreased."),
    (re.compile(r"^play$", re.IGNORECASE), "play", "Playing music."),
]

HELP_PATTERNS: list[re.Pattern] = [
    re.compile(r"^(help|help\s+me|what\s+can\s+i\s+(say|do)\??)$", re.IGNORECASE),
    re.compile(r"^i\s+don'?t\s+know\.?$", re.IGNORECASE),
    re.compile(r"^what\s+(is|are)\s+this\??$", re.IGNORECASE),
    re.compile(r"^what\s+should\s+i\s+(say|do)\??$", re.IGNORECASE),
    # Greetings are harmless and should not be sent to the model.
    re.compile(r"^(hi|hey|hello)?\s*(echo|eko|ecco|eco|ekko|acou|ico|iko)\.?$", re.IGNORECASE),
]

# Phrases used to ask for the currently playing track.
IDENTIFY_PATTERNS: list[re.Pattern] = [
    re.compile(r"^what('?s|\s+is|\s+song\s+is|\s+track\s+is)\s+(this|that|it|playing|on)\b.*$", re.IGNORECASE),
    re.compile(r"^(what|which)\s+(song|track|music)\s+is\s+(this|that|playing|on|it)\b.*$", re.IGNORECASE),
    re.compile(r"^(name|tell\s+me)\s+(the|this|that)?\s*(song|track).*$", re.IGNORECASE),
    re.compile(r"^(current|now)\s+(song|track|playing).*$", re.IGNORECASE),
    re.compile(r"^what('?s|\s+is)\s+(this|that|it)\s+(song|track|called)\??$", re.IGNORECASE),
    re.compile(r"^who\s+(is|sings|sang)\s+this\b.*$", re.IGNORECASE),
]

# Keywords shared by playlist requests and context statements.
PLAYLIST_KEYWORD_MAP: dict[str, str] = {
    # calm
    "calm": "calm",
    "relaxing": "calm",
    "relaxed": "calm",
    "chill": "calm",
    "peaceful": "calm",
    # energy
    "energy": "energy",
    "energetic": "energy",
    "energizing": "energy",
    "motivation": "energy",
    "motivational": "energy",
    "upbeat": "energy",
    "pump": "energy",
    # focus
    "focus": "focus",
    "focused": "focus",
    "study": "focus",
    "studying": "focus",
    "concentrate": "focus",
    "concentration": "focus",
    "ambient": "focus",
    # happy
    "happy": "happy",
    "cheerful": "happy",
    "joyful": "happy",
    "joy": "happy",
    # sad
    "sad": "sad",
    "melancholic": "sad",
    "melancholy": "sad",
    "soothing": "sad",
}

# After removing a phrase such as "I am", these words map to a playlist.
CONTEXT_STATEMENT_MAP: dict[str, str] = {
    # calm
    "tired": "calm",
    "exhausted": "calm",
    "sleepy": "calm",
    "stressed": "calm",
    "anxious": "calm",
    "relaxed": "calm",
    "relax": "calm",
    # energy
    "energy": "energy",
    "energetic": "energy",
    "energized": "energy",
    "motivation": "energy",
    "motivated": "energy",
    "pumped": "energy",
    "working out": "energy",
    # focus
    "focus": "focus",
    "focused": "focus",
    "study": "focus",
    "studying": "focus",
    "concentrate": "focus",
    "concentrating": "focus",
    # happy
    "happy": "happy",
    "excited": "happy",
    "great": "happy",
    "amazing": "happy",
    "wonderful": "happy",
    "joyful": "happy",
    # sad
    "sad": "sad",
    "down": "sad",
    "lonely": "sad",
    "depressed": "sad",
    "blue": "sad",
    "heartbroken": "sad",
}

# A small local filter covers common requests outside the music domain.
OFF_TOPIC_PATTERNS: list[re.Pattern] = [
    re.compile(r"^what\s+(is|are)\s+(?!this\b).+", re.IGNORECASE),
    re.compile(r"^who\s+(is|are|was)\s+.+", re.IGNORECASE),
    re.compile(r"^(where|when|why|how)\s+(is|are|was|do|does|did|can|could)\s+.+", re.IGNORECASE),
    re.compile(r"^tell\s+me\s+(about|a)\s+.+", re.IGNORECASE),
    re.compile(r"^(calculate|compute|solve)\s+.+", re.IGNORECASE),
    re.compile(r"^what.*weather.*$", re.IGNORECASE),
    re.compile(r"^what.*time.*$", re.IGNORECASE),
    re.compile(r"^what.*news.*$", re.IGNORECASE),
]

# Spoken confirmation for each context category.
_CONTEXT_FEEDBACK: dict[str, str] = {
    "calm": "I'll play something calm and relaxing for you.",
    "energy": "Playing energetic music to boost your energy!",
    "focus": "Playing ambient music to help you focus.",
    "happy": "Playing some happy, cheerful music!",
    "sad": "I'll play something soft and soothing for you.",
}


def try_rule_based(text: str) -> Optional[IntentResult]:
    """
    Attempt to classify the input using simple rule-based patterns.

    Returns an IntentResult if matched, None if the AI should handle it.
    Checks in order: empty → direct commands → help → playlist commands
    → context statements → off-topic → generic "play <X>" → None.
    """
    text = text.strip()

    if not text:
        return IntentResult(
            intent_type="unclear",
            action="clarify",
            interpreted_context="none",
            confidence=0.3,
            user_feedback="I didn't catch that. You can say: play something calm, or ask for help.",
        )

    # Try the most specific local rules first.
    for pattern, action, feedback in DIRECT_COMMAND_PATTERNS:
        if pattern.match(text):
            return IntentResult(
                intent_type="direct_command",
                action=action,
                interpreted_context="none",
                confidence=0.98,
                user_feedback=feedback,
            )

    # Help phrases
    for pattern in HELP_PATTERNS:
        if pattern.match(text):
            return IntentResult(
                intent_type="help_request",
                action="help",
                interpreted_context="none",
                confidence=0.98,
                user_feedback=(
                    "You can say: play, pause, next song, volume up, "
                    "or tell me how you feel and I'll find the right music."
                ),
            )

    # Current-track questions
    for pattern in IDENTIFY_PATTERNS:
        if pattern.match(text):
            return IntentResult(
                intent_type="direct_command",
                action="identify",
                interpreted_context="none",
                confidence=0.97,
                user_feedback="Let me check what's playing.",
            )

    # Playlist requests such as "play calm music"
    play_match = re.match(r"^play\s+(.+)$", text, re.IGNORECASE)
    if play_match:
        target = play_match.group(1).strip().lower()
        # Keep only the word that describes the requested playlist.
        clean_target = re.sub(
            r"\s*(music|songs?|playlist|tracks?)$", "", target
        ).strip()
        if clean_target in PLAYLIST_KEYWORD_MAP:
            context = PLAYLIST_KEYWORD_MAP[clean_target]
            return IntentResult(
                intent_type="context_request",
                action="select_playlist",
                interpreted_context=context,
                confidence=0.95,
                user_feedback=_CONTEXT_FEEDBACK.get(
                    context, f"Playing {context} music for you."
                ),
            )
        # A remaining "play ..." phrase may be a track name.
        return IntentResult(
            intent_type="direct_command",
            action="play",
            interpreted_context="none",
            confidence=0.95,
            user_feedback=f"Playing {play_match.group(1).strip()}.",
        )

    # Context statements such as "I am tired" or "I feel sad"
    text_lower = text.lower().rstrip(".!?")
    for prefix in [
        "i am ", "i'm ", "i feel ", "feeling ", "i am feeling ",
        "i'm feeling ", "i need ", "i want ", "i need to ", "i want to ",
    ]:
        if text_lower.startswith(prefix):
            remainder = text_lower[len(prefix):].strip()
            if remainder in CONTEXT_STATEMENT_MAP:
                context = CONTEXT_STATEMENT_MAP[remainder]
                return IntentResult(
                    intent_type="context_request",
                    action="select_playlist",
                    interpreted_context=context,
                    confidence=0.90,
                    user_feedback=_CONTEXT_FEEDBACK.get(
                        context, f"Playing {context} music for you."
                    ),
                )

    # Known off-topic requests can be rejected without an API call.
    for pattern in OFF_TOPIC_PATTERNS:
        if pattern.match(text):
            return IntentResult(
                intent_type="off_topic",
                action="reject",
                interpreted_context="none",
                confidence=0.95,
                user_feedback=(
                    "I'm only specialized in music. "
                    "You can say: play jazz, pause, or play something calm."
                ),
            )

    return None


class IntentClassifier:
    """
    AI-powered intent classifier for Echo-Sync.

    Uses rule-based fast-path for common commands and falls back
    to OpenAI API for complex/ambiguous inputs.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.ai_model

    def classify(self, transcript: str) -> IntentResult:
        """
        Classify user speech transcript into a structured intent.

        First tries rule-based matching for speed and reliability.
        Falls back to AI classification for complex cases.

        Args:
            transcript: The transcribed user speech text.

        Returns:
            IntentResult with classified intent, action, context, and feedback.
        """
        # Local rules cover the commands used most often.
        rule_result = try_rule_based(transcript)
        if rule_result is not None:
            logger.info(
                "Rule-based match: %s → %s",
                transcript,
                rule_result.intent_type,
            )
            return rule_result

        # Use the model only when local rules do not understand the text.
        logger.info("AI classification for: %s", transcript)
        return self._classify_with_ai(transcript)

    def _classify_with_ai(self, transcript: str) -> IntentResult:
        """
        Call the OpenAI API for intent classification.

        Uses structured JSON output format to ensure consistent results.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": INTENT_CLASSIFIER_SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": transcript,
                    },
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=200,
            )

            content = response.choices[0].message.content
            if content is None:
                logger.warning("AI returned empty content")
                return self._fallback_unclear(transcript)

            # Pydantic rejects responses that do not follow the expected shape.
            data = json.loads(content)
            result = IntentResult.model_validate(data)
            logger.info(
                "AI classified '%s' as %s (confidence: %.2f)",
                transcript,
                result.intent_type,
                result.confidence,
            )
            return result

        except json.JSONDecodeError as e:
            logger.error("Failed to parse AI JSON response: %s", e)
            return self._fallback_unclear(transcript)

        except Exception as e:
            logger.error("AI classification error: %s", e)
            return self._fallback_unclear(transcript)

    @staticmethod
    def _fallback_unclear(transcript: str) -> IntentResult:
        """Return a safe fallback when AI classification fails."""
        return IntentResult(
            intent_type="unclear",
            action="clarify",
            interpreted_context="none",
            confidence=0.2,
            user_feedback=(
                "I had trouble understanding that. "
                "You can say: play, pause, next song, or tell me how you feel."
            ),
        )
