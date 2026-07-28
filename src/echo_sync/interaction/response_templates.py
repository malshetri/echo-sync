"""
Echo-Sync response templates.

Pre-built response strings for all system messages.
These are used for spoken feedback to the user via TTS or console output.
"""

# Direct command responses

RESPONSE_PLAY = "Playing music."
RESPONSE_PAUSE = "Music paused."
RESPONSE_RESUME = "Resuming music."
RESPONSE_STOP = "Music stopped."
RESPONSE_NEXT = "Playing next song."
RESPONSE_PREVIOUS = "Playing previous song."
RESPONSE_VOLUME_UP = "Volume increased."
RESPONSE_VOLUME_DOWN = "Volume decreased."

# Context responses

RESPONSE_CONTEXT_TEMPLATE = "I'll play something {description} for you."
RESPONSE_CONTEXT_MAP = {
    "calm": "I'll play something calm and relaxing for you.",
    "energy": "Playing energetic music to boost your energy!",
    "focus": "Playing ambient music to help you focus.",
    "happy": "Playing some happy, cheerful music!",
    "sad": "I'll play something soft and soothing for you.",
    "unknown": "I'll play a mix of music for you.",
}

# Help responses

RESPONSE_HELP_GENERAL = (
    "I can help you control music. You can say: "
    "play jazz, pause, next song, volume up, "
    "or tell me how you feel and I'll find the right music."
)

RESPONSE_HELP_COMMANDS = (
    "Available commands: play, pause, resume, stop, "
    "next song, previous song, volume up, volume down."
)

RESPONSE_HELP_MOODS = (
    "You can tell me how you feel: "
    "I'm tired, I need energy, I want to focus, "
    "I'm happy, I feel sad."
)

# Error and clarification responses

RESPONSE_UNCLEAR = (
    "I didn't quite catch that. "
    "You can say: play, pause, next song, "
    "or tell me how you feel."
)

RESPONSE_SILENCE = (
    "I'm still here. Do you need help? "
    "You can say: play something calm, or ask for help."
)

RESPONSE_LOW_CONFIDENCE = (
    "I'm not quite sure what you mean. "
    "You can say: play, pause, next song, "
    "or tell me how you feel."
)

RESPONSE_STT_FAILED = (
    "I had trouble hearing you. "
    "Could you try again? You can say: play, pause, or help."
)

# Off-topic responses

RESPONSE_OFF_TOPIC = (
    "I'm only specialized in music. "
    "You can say: play jazz, pause, "
    "or play something relaxing."
)

RESPONSE_OFF_TOPIC_GENTLE = (
    "I can only help with music. "
    "Would you like me to play something "
    "calm, energetic, or focused?"
)

# System messages

RESPONSE_WELCOME = (
    "Welcome to Echo-Sync. "
    "I'm your music assistant. "
    "You can say: play jazz, pause, next song, "
    "or tell me how you feel. "
    "Say help at any time for more options."
)

RESPONSE_GOODBYE = "Goodbye! Enjoy your music."

RESPONSE_NO_MUSIC = (
    "I don't have any music files in that category yet. "
    "Would you like to try a different mood?"
)

RESPONSE_PLAYLIST_LOADED = "Playlist loaded with {count} songs."

RESPONSE_PLAYER_ERROR = (
    "I'm having trouble with the music player. "
    "Let me try again."
)


def get_context_response(context: str) -> str:
    """Get the appropriate response for an interpreted context."""
    return RESPONSE_CONTEXT_MAP.get(context, RESPONSE_CONTEXT_MAP["unknown"])


def get_volume_response(action: str, current_volume: int) -> str:
    """Get volume change response with current level."""
    if action == "volume_up":
        return f"Volume increased to {current_volume} percent."
    elif action == "volume_down":
        return f"Volume decreased to {current_volume} percent."
    return f"Volume is at {current_volume} percent."
