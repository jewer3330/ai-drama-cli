"""Cloud AI video backends for the Douyin production pipeline."""

from __future__ import annotations

import mimetypes
import time
from pathlib import Path
from typing import Optional

import requests


class AIVideoError(RuntimeError):
    """Raised when a cloud video job cannot be completed."""


class SoraVideoGenerator:
    """Generate vertical image-to-video clips through the OpenAI Videos API."""

    ALLOWED_SECONDS = (4, 8, 12)
    ALLOWED_SIZES = ("720x1280", "1024x1792")

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "sora-2-pro",
        poll_interval: float = 5.0,
        timeout: float = 900.0,
    ):
        if not api_key:
            raise ValueError("Sora video generation requires an API key")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.poll_interval = max(1.0, poll_interval)
        self.timeout = max(30.0, timeout)

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    @classmethod
    def seconds_for_duration(cls, duration: float) -> int:
        """Pick the smallest supported clip duration that covers the audio."""
        for seconds in cls.ALLOWED_SECONDS:
            if duration <= seconds:
                return seconds
        return cls.ALLOWED_SECONDS[-1]

    def generate(
        self,
        prompt: str,
        output_path: Path,
        reference_image: Optional[Path] = None,
        seconds: int = 8,
        size: str = "720x1280",
    ) -> Path:
        if seconds not in self.ALLOWED_SECONDS:
            raise ValueError(f"seconds must be one of {self.ALLOWED_SECONDS}")
        if size not in self.ALLOWED_SIZES:
            raise ValueError(f"size must be one of {self.ALLOWED_SIZES}")

        data = {
            "model": self.model,
            "prompt": prompt,
            "seconds": str(seconds),
            "size": size,
        }
        files = None
        image_handle = None
        if reference_image:
            image_handle = reference_image.open("rb")
            content_type = mimetypes.guess_type(reference_image.name)[0] or "image/png"
            files = {"input_reference": (reference_image.name, image_handle, content_type)}

        try:
            try:
                response = requests.post(
                    f"{self.base_url}/videos",
                    headers=self.headers,
                    data=data,
                    files=files,
                    timeout=90,
                )
            except requests.RequestException as exc:
                raise AIVideoError(f"Could not create video: {exc}") from exc
        finally:
            if image_handle:
                image_handle.close()

        self._raise_for_error(response, "create video")
        job = response.json()
        video_id = job.get("id")
        if not video_id:
            raise AIVideoError("Videos API returned no job id")

        self._wait_for_completion(video_id)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            content = requests.get(
                f"{self.base_url}/videos/{video_id}/content",
                headers=self.headers,
                timeout=300,
            )
        except requests.RequestException as exc:
            raise AIVideoError(f"Could not download video: {exc}") from exc
        self._raise_for_error(content, "download video")
        output_path.write_bytes(content.content)
        if output_path.stat().st_size < 10_000:
            raise AIVideoError("Downloaded video is unexpectedly small")
        return output_path

    def _wait_for_completion(self, video_id: str) -> None:
        deadline = time.monotonic() + self.timeout
        last_status = "queued"
        while time.monotonic() < deadline:
            try:
                response = requests.get(
                    f"{self.base_url}/videos/{video_id}",
                    headers=self.headers,
                    timeout=60,
                )
            except requests.RequestException as exc:
                raise AIVideoError(f"Could not poll video: {exc}") from exc
            self._raise_for_error(response, "poll video")
            job = response.json()
            last_status = job.get("status", "unknown")
            if last_status == "completed":
                return
            if last_status in {"failed", "cancelled"}:
                error = job.get("error") or {}
                message = error.get("message") if isinstance(error, dict) else str(error)
                raise AIVideoError(message or f"Video job {last_status}")
            time.sleep(self.poll_interval)
        raise AIVideoError(f"Video job timed out while status was {last_status}")

    @staticmethod
    def _raise_for_error(response: requests.Response, action: str) -> None:
        if response.ok:
            return
        try:
            payload = response.json()
            error = payload.get("error", payload)
            message = error.get("message") if isinstance(error, dict) else str(error)
        except ValueError:
            message = response.text[:500]
        raise AIVideoError(f"Could not {action}: HTTP {response.status_code}: {message}")


def build_motion_prompt(scene: dict, visual_style: str = "cinematic") -> str:
    """Turn a drama scene into an identity-preserving image-to-video prompt."""
    actions = [dialogue.get("action", "") for dialogue in scene.get("dialogues", [])]
    action_text = ", ".join(action for action in actions if action)
    return (
        "Create a premium vertical live-action Chinese short-drama shot from the reference image. "
        "Preserve every character's face, age, hairstyle, clothing, and body proportions exactly. "
        f"Setting: {scene.get('location', '')}, {scene.get('time', '')}. "
        f"Visual action: {scene.get('visual_description', '')} {action_text}. "
        f"Style: {visual_style}, restrained natural acting, realistic micro-expressions, subtle hair and fabric motion, "
        "intentional cinematic camera movement, shallow depth of field, physically plausible lighting. "
        "No cuts, no new people, no identity drift, no text, no subtitles, no watermark, no logo."
    )
