"""Exception hierarchy for Liveframe."""


class LiveframeError(Exception):
    """Base exception for all Liveframe errors."""


class VideoFileError(LiveframeError):
    """Input video issues: not found, unreadable, too short, wrong format."""


class FFmpegError(LiveframeError):
    """ffmpeg or ffprobe execution failure."""


class GeminiError(LiveframeError):
    """Base for Gemini API-related errors."""


class FileUploadError(GeminiError):
    """File API upload or processing failure."""


class AnalysisError(GeminiError):
    """generate_content call failure or unparseable response."""


class RateLimitError(GeminiError):
    """429 rate limit from Gemini API."""


class ClipExtractionError(LiveframeError):
    """Individual clip extraction failure."""
