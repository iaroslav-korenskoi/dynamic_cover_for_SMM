#!/usr/bin/env python3
"""Динамическая обложка сообщества ВКонтакте: рисует на фоне текущее время и грузит её в паблик."""

from __future__ import annotations

import logging
import os
import signal
import sys
import tempfile
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import vk_api
from PIL import Image, ImageDraw, ImageFont, ImageOps

BASE_DIR = Path(__file__).resolve().parent

# Актуальный формат обложки сообщества ВК (десктоп): 1590x530.
# На мобильных видна центральная часть шириной ~1196 px — важный текст держим внутри неё.
COVER_SIZE = (1590, 530)
MOBILE_SAFE_WIDTH = 1196

log = logging.getLogger("vkcover")


@dataclass(frozen=True)
class Config:
    token: str
    group_id: int
    background: Path = BASE_DIR / "pics" / "vkcover_0.jpg"
    font: Path = BASE_DIR / "fonts" / "days.ttf"
    timezone: str = "UTC"
    interval: int = 120
    text: str = "Обложка обновилась в {time} ({tz})"
    text_color: tuple[int, int, int] = (193, 0, 32)
    # Центр верхней кромки текста; по умолчанию — правая колонка над надписью фона.
    text_pos: tuple[int, int] = (1035, 40)
    text_max_width: int = 780
    text_max_size: int = 40

    @classmethod
    def from_env(cls) -> "Config":
        try:
            token = os.environ["VK_TOKEN"]
            group_id = int(os.environ["VK_GROUP_ID"])
        except KeyError as e:
            sys.exit(f"Не задана переменная окружения {e.args[0]} (см. README)")
        except ValueError:
            sys.exit("VK_GROUP_ID должен быть числом (без минуса и 'club')")

        env = os.environ.get
        return cls(
            token=token,
            group_id=abs(group_id),
            background=Path(env("COVER_BACKGROUND", cls.background)),
            font=Path(env("COVER_FONT", cls.font)),
            timezone=env("COVER_TZ", cls.timezone),
            interval=int(env("COVER_INTERVAL", cls.interval)),
            text=env("COVER_TEXT", cls.text),
            text_color=_parse_color(env("COVER_COLOR")) or cls.text_color,
            text_pos=_parse_pos(env("COVER_TEXT_POS")) or cls.text_pos,
            text_max_width=int(env("COVER_TEXT_MAX_WIDTH", cls.text_max_width)),
            text_max_size=int(env("COVER_TEXT_MAX_SIZE", cls.text_max_size)),
        )


def _parse_color(value: str | None) -> tuple[int, int, int] | None:
    if not value:
        return None
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _parse_pos(value: str | None) -> tuple[int, int] | None:
    if not value:
        return None
    x, y = value.split(",")
    return int(x), int(y)


def render_cover(cfg: Config, now: datetime) -> Image.Image:
    """Вписывает фон в размер обложки (с обрезкой по центру) и рисует поверх него текст со временем."""
    with Image.open(cfg.background) as src:
        cover = ImageOps.fit(src.convert("RGB"), COVER_SIZE, Image.LANCZOS)

    text = cfg.text.format(time=now.strftime("%H:%M"), tz=now.tzname())
    draw = ImageDraw.Draw(cover)

    # Подбираем максимально крупный шрифт, при котором текст влезает в отведённую ширину.
    size = cfg.text_max_size
    font = ImageFont.truetype(str(cfg.font), size)
    while size > 10 and draw.textlength(text, font=font) > cfg.text_max_width:
        size -= 2
        font = ImageFont.truetype(str(cfg.font), size)

    draw.text(
        cfg.text_pos,
        text,
        font=font,
        fill=cfg.text_color,
        anchor="mt",
    )
    return cover


def upload_cover(upload: vk_api.VkUpload, cfg: Config, cover: Image.Image) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "cover.png"
        cover.save(path)
        upload.photo_cover(str(path), cfg.group_id, 0, 0, *COVER_SIZE)


def run(cfg: Config) -> None:
    upload = vk_api.VkUpload(vk_api.VkApi(token=cfg.token))
    tz = ZoneInfo(cfg.timezone)
    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())

    while not stop.is_set():
        try:
            upload_cover(upload, cfg, render_cover(cfg, datetime.now(tz)))
            log.info("Обложка обновлена")
        except (vk_api.VkApiError, OSError) as e:
            # Сетевые сбои и ошибки API не должны убивать долгоживущий процесс.
            log.error("Не удалось обновить обложку: %s", e)
        stop.wait(cfg.interval)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run(Config.from_env())


if __name__ == "__main__":
    main()
