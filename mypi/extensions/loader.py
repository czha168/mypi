from __future__ import annotations
import importlib.util
import inspect
import logging
import sys
from pathlib import Path
from mypi.extensions.base import Extension

logger = logging.getLogger(__name__)


class ExtensionLoader:
    def __init__(self, extensions_dir: Path):
        self.extensions_dir = Path(extensions_dir)
        self.extensions: list[Extension] = []
        self._observer = None

    def load(self) -> list[Extension]:
        """Scan extensions_dir for .py files, import, instantiate Extension subclasses."""
        self.extensions = []
        if not self.extensions_dir.exists():
            return []
        for py_file in sorted(self.extensions_dir.glob("*.py")):
            self._load_file(py_file)
        return self.extensions

    def start_watching(self, on_idle: "Callable[[], bool]") -> None:
        """Start watchdog observer. Hot-reload is deferred until on_idle() returns True."""
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler

            loader = self

            class Handler(FileSystemEventHandler):
                def on_modified(self, event):
                    if event.src_path.endswith(".py"):
                        if on_idle():
                            logger.info(f"Hot-reloading extensions (triggered by {event.src_path})")
                            loader.load()

            self._observer = Observer()
            self._observer.schedule(Handler(), str(self.extensions_dir), recursive=False)
            self._observer.start()
        except ImportError:
            logger.warning("watchdog not installed — hot-reload disabled")

    def stop_watching(self) -> None:
        if self._observer:
            self._observer.stop()
            self._observer.join()

    def _load_file(self, path: Path) -> None:
        module_name = f"mypi_ext_{path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            return
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            logger.error(f"Failed to load extension {path.name}: {e}")
            return
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if (issubclass(obj, Extension) and obj is not Extension
                    and not inspect.isabstract(obj)):
                try:
                    instance = obj()
                    self.extensions.append(instance)
                    logger.info(f"Loaded extension: {instance.name}")
                except Exception as e:
                    logger.error(f"Failed to instantiate {obj.__name__}: {e}")
