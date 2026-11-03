"""
pixmap_utils.py -- Async Pixmap Loader + LRU Cache
====================================================
Load anh/thumbnail tren background thread, tranh block UI thread chinh.

Usage:
    from pixmap_utils import AsyncPixmapLoader, PixmapCache, load_pixmap_async

    # Load anh len label bat dong bo:
    load_pixmap_async(lbl, "/path/to/img.jpg", max_w=90, max_h=90)
"""
from __future__ import annotations
from pathlib import Path
from collections import OrderedDict
from typing import Optional, Callable

from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QPixmap


# ---------------------------------------------------------------------------
# LRU Pixmap Cache
# ---------------------------------------------------------------------------
MAX_CACHE_ENTRIES = 300  # anh toi da giu trong RAM

class PixmapCache:
    """Thread-safe LRU cache cho QPixmap (key = duong dan + kich thuoc)."""
    _store: OrderedDict[str, QPixmap] = OrderedDict()

    @classmethod
    def _key(cls, path: str, max_w: int, max_h: int) -> str:
        return f"{path}@{max_w}x{max_h}"

    @classmethod
    def get(cls, path: str, max_w: int, max_h: int) -> Optional[QPixmap]:
        k = cls._key(path, max_w, max_h)
        if k in cls._store:
            cls._store.move_to_end(k)
            return cls._store[k]
        return None

    @classmethod
    def put(cls, path: str, max_w: int, max_h: int, pix: QPixmap) -> None:
        k = cls._key(path, max_w, max_h)
        cls._store[k] = pix
        cls._store.move_to_end(k)
        if len(cls._store) > MAX_CACHE_ENTRIES:
            cls._store.popitem(last=False)

    @classmethod
    def invalidate(cls, path: str) -> None:
        """Xoa cache cho mot anh cu the (khi anh bi ghi de)."""
        keys_to_del = [k for k in cls._store if k.startswith(path + "@")]
        for k in keys_to_del:
            del cls._store[k]

    @classmethod
    def clear(cls) -> None:
        cls._store.clear()


# ---------------------------------------------------------------------------
# Background loader worker
# ---------------------------------------------------------------------------
class AsyncPixmapLoader(QThread):
    """Load + scale QImage tren background thread, emit ve main thread."""
    ready = pyqtSignal(object, object)   # (target_label_or_callable, QImage)

    def __init__(self, target, path: str, max_w: int, max_h: int,
                 placeholder_text: str = "...", parent=None):
        super().__init__(parent)
        self.target     = target
        self.path       = path
        self.max_w      = max_w
        self.max_h      = max_h

    def run(self):
        try:
            from PyQt6.QtGui import QImage
            if not self.path or not Path(self.path).exists():
                self.ready.emit(self.target, QImage())
                return

            qimg = QImage(self.path)
            if not qimg.isNull():
                qimg = qimg.scaled(
                    self.max_w, self.max_h,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            self.ready.emit(self.target, qimg)
        except Exception:
            from PyQt6.QtGui import QImage
            self.ready.emit(self.target, QImage())


# ---------------------------------------------------------------------------
# Active loader registry (prevent GC of running threads)
# ---------------------------------------------------------------------------
_active_loaders: list[AsyncPixmapLoader] = []

def _cleanup_loaders():
    global _active_loaders
    _active_loaders = [l for l in _active_loaders if l.isRunning()]


# ---------------------------------------------------------------------------
# Convenience helper
# ---------------------------------------------------------------------------
def load_pixmap_async(
    label: QLabel,
    path: str,
    max_w: int = 90,
    max_h: int = 90,
    on_ready: Optional[Callable[[QPixmap], None]] = None,
) -> None:
    """
    Load anh bat dong bo va set vao label.
    - Kiem tra cache truoc; neu co, set ngay (dong bo, nhanh).
    - Neu miss cache, load QImage tren background thread, convert sang QPixmap tren main thread.
    - on_ready: callback tuy chon nhan (QPixmap) thay vi auto set label.
    """
    if not path:
        return

    # Cache hit -> dong bo
    cached = PixmapCache.get(path, max_w, max_h)
    if cached is not None:
        if on_ready:
            on_ready(cached)
        elif label:
            try:
                if not cached.isNull():
                    label.setPixmap(cached)
            except RuntimeError:
                pass
        return

    # Cache miss -> background
    loader = AsyncPixmapLoader(label, path, max_w, max_h)

    def _apply(tgt, qimg):
        _cleanup_loaders()
        from PyQt6.QtGui import QPixmap
        pix = QPixmap()
        if qimg and not qimg.isNull():
            pix = QPixmap.fromImage(qimg)
            PixmapCache.put(path, max_w, max_h, pix)

        if on_ready:
            try:
                on_ready(pix)
            except Exception:
                pass
        elif tgt is not None:
            try:
                if not pix.isNull():
                    tgt.setPixmap(pix)
            except RuntimeError:
                pass

    loader.ready.connect(_apply)
    _active_loaders.append(loader)
    loader.start()
