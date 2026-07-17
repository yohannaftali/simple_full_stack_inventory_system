import importlib
import importlib.util
import inspect
import sys
import traceback
from pathlib import Path

import flet as ft

from pages.error import ErrorPage


class ModuleLoader:
    """Load and cache all item screens at startup"""

    # Class-level cache shared across all instances to prevent reload loops
    _global_cache = {}
    _preload_complete = False

    def __init__(self, page: ft.Page, target: str):
        self.page = page
        self.cache = ModuleLoader._global_cache
        self.target = target  # modules or modals
        self.page_class = None
        if target == "modules":
            self.page_class = "ModulePage"
        elif target == "modals":
            self.page_class = "ModalPage"

    def is_preloaded(self) -> bool:
        """Check if modules have already been preloaded"""
        return ModuleLoader._preload_complete

    @staticmethod
    def reset_cache():
        """Drop every preloaded pages.modules/pages.modals module from
        sys.modules and clear the shared cache, so the next preload()/
        load() re-imports everything fresh instead of reusing stale
        objects. Used by main.py's dev-only "Reload Library" recovery and
        the Troubleshooting page's hard reset."""
        for key in list(sys.modules):
            if key.startswith("pages.modules.") or key.startswith("pages.modals."):
                del sys.modules[key]
        ModuleLoader._global_cache.clear()
        ModuleLoader._preload_complete = False

    @staticmethod
    def list_implemented(target: str) -> set[str]:
        """List item names with an implemented screen dir under pages/<target>

        Does not import anything - just scans directory names, so it's cheap
        enough to call for UI filtering (e.g. the home module list).
        """
        current_dir = Path(__file__).parent.parent
        target_dir = current_dir / "pages" / target
        if not target_dir.exists():
            return set()

        return {
            item_dir.name
            for item_dir in target_dir.iterdir()
            if item_dir.is_dir()
            and not item_dir.name.startswith("_")
            and item_dir.name != "example"
        }

    def preload(self, on_progress=None) -> dict:
        """Scan item in target directory

        Args:
            on_progress: optional callback invoked as
                `on_progress(loaded, total, item, screen)` after each screen
                is preloaded (or found not-importable), for driving a splash
                screen progress bar.
        """
        result: dict = {}
        current_dir = Path(__file__).parent.parent
        target_dir = current_dir / "pages" / self.target
        if not target_dir.exists():
            print(f"Target directory not found: {target_dir}")
            return result

        # First pass: collect (item, screen) pairs so the total is known
        # up-front for progress reporting.
        screens: list[tuple[str, str]] = []
        for item_dir in target_dir.iterdir():
            if not item_dir.is_dir():
                continue
            if item_dir.name.startswith("_"):
                continue

            item_name = item_dir.name
            result[item_name] = []

            for screen_file in item_dir.glob("*.py"):
                if screen_file.name.startswith("_"):
                    continue
                screen_name = screen_file.stem  # filename without .py
                result[item_name].append(screen_name)
                screens.append((item_name, screen_name))

        total = len(screens)
        for loaded, (item_name, screen_name) in enumerate(screens, start=1):
            self._preload_screen(item_name, screen_name)
            if on_progress is not None:
                on_progress(loaded, total, item_name, screen_name)

        ModuleLoader._preload_complete = True
        print(f"✓ Preloaded {len(self.cache)} item screens")
        return result

    def _preload_screen(self, item: str, screen: str):
        """Preload a single module screen"""
        path = f"pages.{self.target}.{item}.{screen}"
        cache_key = f"{item}/{screen}"

        try:
            # Check if item exists
            spec = importlib.util.find_spec(path)
            if spec is None:
                print(f"not found /{self.target}/{item}/{screen}.py")
                return

            # Import the item
            print(f"  Loading {cache_key}...")
            imported_module = importlib.import_module(path)

            # Cache it
            self.cache[cache_key] = imported_module
            print(f"  ✓ Cached {cache_key}")

        except Exception as e:
            print(f"  ✗ Failed to preload {cache_key}: {type(e).__name__}: {e}")
            traceback.print_exc()

    def get_module(self, module: str, screen: str):
        """Get a cached module or return None if not found"""
        cache_key = f"{module}/{screen}"
        return self.cache.get(cache_key)

    def is_cached(self, module: str, screen: str) -> bool:
        """Check if a module is cached"""
        cache_key = f"{module}/{screen}"
        return cache_key in self.cache

    def load(self, item: str, screen: str):
        """Dynamically import a item's screen component

        Always reloads from `sys.modules` when the module is already
        imported there, so edits made after the first visit to a screen
        take effect on the next navigation (important for `flet run -r`
        hot-reload, where the process stays alive across edits). Falls
        back to the preload cache, then to a fresh import.

        Returns:
            item object if successful, None if item not found or error
        """
        path = f"pages.{self.target}.{item}.{screen}"
        cache_key = f"{item}/{screen}"

        try:
            # Already imported in this process: reload to pick up edits
            if path in sys.modules:
                print(f"Item {path} found in sys.modules, reloading")
                imported_module = importlib.reload(sys.modules[path])
                self.cache[cache_key] = imported_module
                print(f"✓ Successfully reloaded {path}")
                return imported_module

            # Fall back to the preload cache
            cached = self.get_module(item, screen)
            if cached is not None:
                print(f"✓ Using cached item: {item}/{screen}")
                return cached

            # Not imported or cached yet: import fresh
            print(f"Checking if item {path} exists...")
            spec = importlib.util.find_spec(path)
            if spec is None:
                print(f"ERROR: Item {path} not found!")
                return None

            print(f"Item {path} found, importing...")
            imported_module = importlib.import_module(path)
            self.cache[cache_key] = imported_module
            print(f"✓ Successfully imported {path}")
            return imported_module

        except ModuleNotFoundError as e:
            print(f"ERROR: Item not found: {path} - {e}")
            return None
        except Exception as e:
            print(f"ERROR: Failed to import {path}: {type(e).__name__}: {e}")
            traceback.print_exc()
            return None

    def parse_route(self, route: str):
        """Parse an item route of the form /{self.target}/<item>/<screen?>[/<id>?]

        Returns a tuple `(item, screen, record_id)` where `record_id` is
        optional and will be `None` if not present.
        """
        parts = route.strip("/").split("/")
        if len(parts) >= 2 and parts[0] == self.target:
            item = parts[1]
            screen = parts[2] if len(parts) > 2 else "index"
            record_id = parts[3] if len(parts) > 3 else None
            # Strip querystring from record_id if present
            if isinstance(record_id, str) and "?" in record_id:
                record_id = record_id.split("?", 1)[0]
            return item, screen, record_id
        return None, None, None

    def build(self, item: str, screen: str, record_id: str | None = None):
        page_library = self.load(item, screen)
        if page_library is None:
            self.page.views.clear()
            self.page.views.append(
                ErrorPage(
                    self.page,
                    self.target,
                    item,
                    screen,
                    f"Import {item} failed, please restart application, if problem persist please contact IT Support",
                ).build()
            )
        else:
            try:
                PageClass = getattr(page_library, self.page_class)
                # Inspect the constructor's own parameter list rather than
                # try/except TypeError - the latter used to retry the whole
                # construction (a second round of HTTP GETs, this time
                # missing `record_id`, since it's only patched on via
                # setattr afterward) whenever __init__'s *body* raised any
                # TypeError for an unrelated reason (e.g. summing a raw
                # numeric string), misreading it as "this ModulePage doesn't
                # accept record_id" - masking the real error behind a
                # confusing, several-steps-removed HTTP 422 instead of a
                # visible traceback.
                accepts_record_id = "record_id" in inspect.signature(PageClass).parameters
                if accepts_record_id:
                    page_class = PageClass(self.page, item, screen, record_id)
                else:
                    page_class = PageClass(self.page, item, screen)
                    if record_id is not None:
                        setattr(page_class, "record_id", record_id)
                self.page.views.clear()
                self.page.views.append(page_class.build())
                print(f"Page loaded: {item}/{screen}")

            except AttributeError as e:
                self.page.views.clear()
                self.page.views.append(
                    ErrorPage(
                        self.page,
                        self.target,
                        item,
                        screen,
                        f"Error: Building page {item}/{screen}: {e}",
                    ).build()
                )
            except Exception as e:
                self.page.views.clear()
                self.page.views.append(
                    ErrorPage(
                        self.page,
                        self.target,
                        item,
                        screen,
                        f"Unexpected error building {item}/{screen}: {e}",
                    ).build()
                )
