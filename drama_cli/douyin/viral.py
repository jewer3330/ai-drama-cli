"""Helpers for punchier short-video packaging."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .templates import DramaTemplate


@dataclass
class ViralPackage:
    """Publishing copy and edit beats for a vertical short."""

    opening_hook: str
    cover_headline: str
    cover_subhead: str
    outro_cta: str
    publish_title: str
    caption: str
    hashtags: list[str] = field(default_factory=list)
    beat_sheet: list[str] = field(default_factory=list)


def build_viral_package(script: dict, template: Optional[DramaTemplate]) -> ViralPackage:
    """Create a reusable packaging bundle from a script."""
    title = _clean(script.get("title") or "短剧")
    genre = _clean(script.get("genre") or (template.genre if template else "短剧"))
    description = _clean(script.get("description") or "")
    twist_points = list(template.twist_points) if template else []
    tags = list(template.tags) if template else []

    opener = _pick_opening_hook(title, genre, twist_points, description)
    headline = _truncate(_pick_cover_headline(title, genre, description), 16)
    subhead = _truncate(_pick_cover_subhead(twist_points, description), 18)
    cta = _pick_cta(genre)
    publish_title = _truncate(f"{headline}｜{subhead}", 28)

    hashtags = _normalize_tags(tags, genre, title)
    caption = f"{publish_title}。{cta} {' '.join(hashtags[:6])}".strip()
    beat_sheet = _build_beats(script, twist_points)

    return ViralPackage(
        opening_hook=opener,
        cover_headline=headline,
        cover_subhead=subhead,
        outro_cta=cta,
        publish_title=publish_title,
        caption=caption,
        hashtags=hashtags,
        beat_sheet=beat_sheet,
    )


def _pick_opening_hook(title: str, genre: str, twist_points: list[str], description: str) -> str:
    if "契约" in title + description and "十年" in description:
        return "她以为是三年交易，他却等了她整整十年"
    if "复仇" in genre or "重生" in genre:
        return "她这次回来，不是认命，是来清算的"
    if "总裁" in title or "豪门" in genre:
        return "所有人都以为她输定了，结果他当场护到底"
    if "悬疑" in genre or "推理" in genre:
        return "真相只差一步，但最危险的人就在身边"
    if "战神" in genre:
        return "他沉默回城三年，这一次没人拦得住"
    if twist_points:
        return f"开局就爆雷：{_truncate(twist_points[0], 10)}"
    return _truncate(description or f"{title}，一上来就把冲突拉满", 24)


def _pick_cover_headline(title: str, genre: str, description: str) -> str:
    if "契约" in title + description and "十年" in description:
        return "总裁等她十年"
    if "总裁" in title:
        return "总裁当众护妻"
    if "复仇" in genre or "重生" in genre:
        return "重生后她杀疯了"
    if "豪门" in genre:
        return "真千金不装了"
    if "悬疑" in genre:
        return "凶手竟在身边"
    if "战神" in genre:
        return "战神回归全场跪"
    return _truncate(title or description or "高能反转短剧", 16)


def _pick_cover_subhead(twist_points: list[str], description: str) -> str:
    if "契约" in description and "十年" in description:
        return "契约是假的 / 深情是真的"
    if twist_points:
        return " / ".join(_truncate(point, 6) for point in twist_points[:2])
    if description:
        return _truncate(description, 18)
    return "三秒入戏，全程高能"


def _pick_cta(genre: str) -> str:
    if "悬疑" in genre or "推理" in genre:
        return "看到最后再下结论。"
    if "甜" in genre or "恋" in genre:
        return "后面更甜，也更狠。"
    return "后面还有更大的反转。"


def _normalize_tags(tags: list[str], genre: str, title: str) -> list[str]:
    seen = set()
    ordered: list[str] = []
    for raw in tags + [f"#{genre}", f"#{_truncate(title, 10)}", "#短剧", "#短视频", "#抖音短剧"]:
        tag = raw if raw.startswith("#") else f"#{raw}"
        tag = tag.replace(" ", "")
        if tag and tag not in seen:
            ordered.append(tag)
            seen.add(tag)
    return ordered


def _build_beats(script: dict, twist_points: list[str]) -> list[str]:
    beats: list[str] = []
    episodes = script.get("episodes", [])
    for ep in episodes[:3]:
        scenes = ep.get("scenes", [])
        if not scenes:
            continue
        first_scene = scenes[0]
        first_line = ""
        dialogues = first_scene.get("dialogues", [])
        if dialogues:
            first_line = _truncate(dialogues[0].get("line", ""), 18)
        beat = f"第{ep.get('episode_number', 0)}集开场：{first_scene.get('location', '高压现场')}"
        if first_line:
            beat += f"｜首句 {first_line}"
        beats.append(beat)
    for point in twist_points[:3]:
        beats.append(f"反转点：{point}")
    if not beats:
        beats.append("开场三秒上冲突，中段给爆点，结尾留钩子。")
    return beats


def _clean(value: str) -> str:
    return " ".join(str(value).strip().split())


def _truncate(value: str, limit: int) -> str:
    text = _clean(value)
    return text if len(text) <= limit else text[: max(limit - 1, 1)] + "…"
