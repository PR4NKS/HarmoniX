"""Custom exceptions and error hierarchy for HarmoniX music bot."""


class MusicBotException(Exception):
    """Base exception for all music bot errors."""

    def __init__(self, message: str = "An unexpected music bot error occurred."):
        super().__init__(message)
        self.message = message


class VoiceConnectionError(MusicBotException):
    """Raised when failing to connect or communicate with a voice channel."""
    pass


class UserNotInVoiceChannel(VoiceConnectionError):
    """Raised when an interaction user is not in a voice channel."""

    def __init__(self, message: str = "You must be in a voice channel to use this command."):
        super().__init__(message)


class BotNotInVoiceChannel(VoiceConnectionError):
    """Raised when the bot is expected to be in a voice channel but is not."""

    def __init__(self, message: str = "I am not currently connected to any voice channel."):
        super().__init__(message)


class DifferentVoiceChannel(VoiceConnectionError):
    """Raised when the user is in a different voice channel than the bot."""

    def __init__(self, message: str = "You must be in the same voice channel as me to control playback."):
        super().__init__(message)


class TrackNotFoundError(MusicBotException):
    """Raised when a track search yields no playable results."""

    def __init__(self, query: str = ""):
        message = f"No playable tracks were found matching `{query}`." if query else "No tracks found."
        super().__init__(message)


class QueueEmptyError(MusicBotException):
    """Raised when an operation requires tracks in the queue, but none exist."""

    def __init__(self, message: str = "The queue is currently empty."):
        super().__init__(message)


class QueueFullError(MusicBotException):
    """Raised when the queue has reached its maximum configured capacity."""

    def __init__(self, max_size: int):
        super().__init__(f"Queue has reached its limit of {max_size} tracks.")


class InvalidTrackIndexError(MusicBotException):
    """Raised when a requested queue index is out of range."""

    def __init__(self, index: int):
        super().__init__(f"Track at index #{index} does not exist in the queue.")


class PermissionDeniedError(MusicBotException):
    """Raised when a user lacks required permissions."""

    def __init__(self, message: str = "You do not have permission to execute this command."):
        super().__init__(message)


class DJRoleRequiredError(PermissionDeniedError):
    """Raised when a command requires DJ role or administrator privileges."""

    def __init__(self, role_name: str = "DJ"):
        super().__init__(f"This action requires the `{role_name}` role or Administrator permissions.")


class LavalinkUnavailableError(MusicBotException):
    """Raised when Lavalink audio node is offline or unreachable."""

    def __init__(self, message: str = "Audio backend node is currently unavailable. Please try again shortly."):
        super().__init__(message)


class InvalidFilterError(MusicBotException):
    """Raised when an unsupported or malformed audio filter is specified."""
    pass


class InvalidVolumeError(MusicBotException):
    """Raised when an invalid volume level is passed."""

    def __init__(self, message: str = "Volume must be an integer between 0 and 100."):
        super().__init__(message)


class InvalidSeekError(MusicBotException):
    """Raised when a seek timestamp is out of track bounds."""

    def __init__(self, message: str = "Cannot seek beyond the duration of the current track."):
        super().__init__(message)


class PlaylistTooLargeError(MusicBotException):
    """Raised when a playlist exceeds the maximum allowable track import count."""

    def __init__(self, max_size: int):
        super().__init__(f"Playlist exceeds the maximum allowed size of {max_size} tracks.")


class PlatformRestrictedError(MusicBotException):
    """Raised when a source URL or platform cannot be fetched due to terms or restrictions."""

    def __init__(self, message: str = "This source is restricted or cannot be loaded."):
        super().__init__(message)
