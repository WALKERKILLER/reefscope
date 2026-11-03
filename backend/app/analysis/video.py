"""Sequential decoding with PTS-first frame times, shared by every video adapter."""
import math


def open_video(path):
    import cv2
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError("video_decode_failed")
    fps = capture.get(cv2.CAP_PROP_FPS)
    total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    width, height = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)), int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if width <= 0 or height <= 0:
        capture.release()
        raise ValueError("invalid_video_dimensions")
    return capture, fps, total, width, height


class FrameClock:
    """Decoder PTS first; frame/fps only when PTS is unusable and the rate is valid. Counts every fallback."""

    def __init__(self, fps):
        self.fps = fps
        self.previous_ms = -1
        self.fallbacks = 0

    def stamp(self, frame_index, timestamp):
        if not math.isfinite(timestamp) or timestamp < 0 or (frame_index and timestamp <= self.previous_ms):
            if timestamp > 0 and timestamp < self.previous_ms:
                raise ValueError("video_time_reversed")
            if not math.isfinite(self.fps) or self.fps <= 0:
                raise ValueError("video_time_unavailable")
            timestamp = frame_index * 1000 / self.fps
            self.fallbacks += 1
        if timestamp <= self.previous_ms:
            raise ValueError("video_time_invalid")
        self.previous_ms = timestamp
        return timestamp
