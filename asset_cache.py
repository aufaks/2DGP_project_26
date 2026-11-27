from functools import lru_cache
from pathlib import Path

from pico2d import load_image as _load_image


@lru_cache(maxsize=None)
def _load_image_cached(path):
    return _load_image(path)


def load_image(path):
    return _load_image_cached(str(Path(path).resolve()))
