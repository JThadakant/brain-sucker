"""Transcriber seam. Production adapter = faster-whisper large-v3 on CUDA (never turbo: it degrades Thai)."""
import os
from pathlib import Path
from typing import Protocol

from brainsuck.models import Segment
from brainsuck.transcript import UNCLEAR_LOGPROB


class Transcriber(Protocol):
    def transcribe(self, audio: Path, lang: str) -> list[Segment]: ...
    def transcribe_clip(self, audio: Path, lang: str | None, prompt: str) -> tuple[list[Segment], str]: ...


def _add_cublas_dlls() -> None:
    """The pinned nvidia-cublas-cu12 wheel ships DLLs that ctranslate2 must find before it loads (Windows)."""
    try:
        import nvidia.cublas
    except ImportError:
        return
    for d in nvidia.cublas.__path__:
        b = Path(d) / "bin"
        if b.exists():
            os.add_dll_directory(str(b))
            os.environ["PATH"] = str(b) + os.pathsep + os.environ["PATH"]


class FasterWhisperTranscriber:
    def __init__(self, model: str = "large-v3", batch_size: int = 8):
        _add_cublas_dlls()
        from faster_whisper import BatchedInferencePipeline, WhisperModel

        self._pipe = BatchedInferencePipeline(model=WhisperModel(model, device="cuda", compute_type="float16"))
        self.batch_size = batch_size

    def transcribe(self, audio: Path, lang: str) -> list[Segment]:
        segments, _ = self._pipe.transcribe(str(audio), language=lang, batch_size=self.batch_size)
        return [Segment(s.start, s.text.strip()) for s in segments]

    def transcribe_clip(self, audio: Path, lang: str | None, prompt: str) -> tuple[list[Segment], str]:
        """lang=None lets Whisper detect the language; returns segments and the language used."""
        segments, info = self._pipe.transcribe(str(audio), language=lang, initial_prompt=prompt or None,
                                               batch_size=self.batch_size)
        return [Segment(s.start, s.text.strip(), s.avg_logprob < UNCLEAR_LOGPROB) for s in segments], info.language
