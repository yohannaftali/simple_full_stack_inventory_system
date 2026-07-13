import sys

# Force line-buffered stdout so print() output isn't lost if the process is
# killed abruptly (e.g. by the hot-reload watchdog) - fully-buffered stdout
# (the default when piped, as `flet run` does) can silently drop the last
# partial buffer on a hard kill, hiding exactly the evidence needed to find
# what happened right before a crash/restart.
sys.stdout.reconfigure(line_buffering=True)

# Prevent writing __pycache__/*.pyc files. The dev server's hot-reload file
# watcher (flet run -r) watches all files recursively; importing a screen
# (all of them are preloaded at startup - see main()) writes a fresh .pyc,
# which the watcher sees as a file change and triggers a restart mid-import
# while the event loop is blocked doing that very import, freezing the app.
# Never writing bytecode removes the trigger entirely.
sys.dont_write_bytecode = True

from utils.app_logger import setup_logging

# Capture every print() call into an in-memory buffer + rotating log file
# before anything else runs, so the Troubleshooting page's "Show Logs"
# button has data from the very start of this process, including in a
# packaged build with no attached console.
setup_logging()

import asyncio

import flet as ft

from components.loading_overlay import LoadingOverlay
from components.splash_screen import SplashScreen
from pages.error import ErrorPage
from pages.home import HomePage
from pages.login import LoginPage
from pages.server_config import ServerConfigPage
from pages.troubleshooting import TroubleshootingPage
from repository.server_url import DEFAULT_SERVER_URL
from repository.storage import Storage
from utils.module_loader import ModuleLoader
from utils.storage_compat import sp_call_with_retry


async def main(page: ft.Page):
    page.title = "SFSIS"
    page.padding = 0
    page.adaptive = True

    # Custom typefaces referenced by themes/light_theme.py and
    # themes/dark_theme.py's TextTheme (Montserrat for display/headline/
    # title, Lato for body/label - matches frontend/design/material-theme's
    # Compose export, the complete reference for this app's theme). page.fonts
    # needs a direct .ttf/.otf/.ttc URL, not a Google Fonts CSS stylesheet URL.
    page.fonts = {
        "Montserrat": (
            "https://fonts.gstatic.com/s/montserrat/v31/"
            "JTUHjIg1_i6t8kCHKm4532VJOt5-QNFgpCtr6Hw5aX8.ttf"
        ),
        "Lato": (
            "https://fonts.gstatic.com/s/lato/v25/S6uyw4BMUTPHjx4wWw.ttf"
        ),
    }

    # Set window size only for desktop mode
    if hasattr(page, "window") and page.window:
        page.window.width = 400
        page.window.height = 600

    # Show the splash screen immediately so there's something on screen
    # during the startup work below (storage load + module/modal preload),
    # instead of a blank page.
    splash = SplashScreen(page)
    page.views.append(splash.build())
    page.update()

    # Initialize storage for global access
    storage = Storage(page)

    # Web only: give the client a moment to finish mounting the
    # SharedPreferences service before the first invoke, to reduce the
    # client-side "Timeout waiting for invoke method listener" race. Native
    # platforms persist to a file (no service), so they skip this delay.
    if bool(getattr(page, "web", False)):
        await asyncio.sleep(0.5)

    # Load persisted values (theme, server url, cookies, user session) from
    # SharedPreferences into the in-memory page.data cache. Must happen
    # before anything reads storage.*.get(), since SharedPreferences is
    # async-only in Flet 0.85 (there is no synchronous client_storage
    # anymore).
    splash.set_progress(None, "Loading ...")
    await storage.load_persistent()

    # Preloading used to be disabled here because importing every screen
    # wrote __pycache__/*.pyc files, which the `flet run -r` file watcher
    # saw as a change and used to trigger a restart mid-import (freezing the
    # app). `sys.dont_write_bytecode = True` above removes that trigger, so
    # preloading is safe to run under hot reload too.
    modules = ModuleLoader(page=page, target="modules")
    modals = ModuleLoader(page=page, target="modals")

    def _report_progress(loaded: int, total: int, item: str, screen: str):
        fraction = loaded / total if total else 1.0
        splash.set_progress(fraction, f"Loading {item}/{screen}...")

    def _preload_all():
        splash.set_progress(0, "Loading modules...")
        modules.preload(on_progress=_report_progress)
        splash.set_progress(0, "Loading modals...")
        modals.preload(on_progress=_report_progress)
        splash.set_progress(1, "Ready")

    _preload_all()
    storage.set("modules", {})
    storage.set("modals", {})

    # Store last route to detect same-route navigation
    last_route = {"value": None}

    # Show loading overlay BEFORE clearing views
    loading_overlay = LoadingOverlay(page, "Loading...")
    page.overlay.append(loading_overlay.build())
    page.update()

    async def route_change(route):
        """Handle route changes"""
        print(f"route to: {page.route} from: {last_route['value']}")
        loading_overlay.show()
        # route_change runs synchronously on the event loop, and building the
        # destination view below makes blocking HTTP calls (via `requests`)
        # that freeze the loop entirely - without yielding here, the "show"
        # update queued above never actually reaches the client before the
        # freeze starts, so the loader never gets painted. One loop tick is
        # enough for the client to render it before the blocking work begins.
        await asyncio.sleep(0.05)

        # Clear active tables when changing routes
        if hasattr(page, "data") and isinstance(page.data, dict):
            page.data["active_tables"] = []

        page.views.clear()
        last_route["value"] = page.route

        if page.route in {"/login", "/"}:
            login_page = LoginPage(page)
            page.views.append(login_page.build())
            storage.home_search.clear()
            storage.table_search.clear()
        elif page.route == "/home":
            home_page = HomePage(page)
            page.views.append(home_page.build())
            storage.module_history.clear()
        elif page.route == "/server_config":
            config_page = ServerConfigPage(page)
            page.views.append(config_page.build())
        elif page.route == "/troubleshooting":
            troubleshooting_page = TroubleshootingPage(page)
            page.views.append(troubleshooting_page.build())
        elif page.route.startswith("/modules/"):
            module, screen, record_id = modules.parse_route(page.route)
            if module is None:
                page.views.append(
                    ErrorPage(
                        page, "modules", "unknown", "index", "Route incomplete"
                    ).build()
                )
            else:
                # Run the blocking permission check + page build off the event
                # loop. They make synchronous `requests` calls that otherwise
                # freeze the asyncio loop for seconds; on desktop that stalls
                # the Flet host connection long enough that `flet run -r`
                # respawns the whole process (new PID) mid-navigation. The
                # build path is update-free (List.get_data runs in __init__ with
                # body=None, so no control.update() fires) - only the single
                # page.update() below touches the UI, and it stays on the loop.
                has_access = await asyncio.to_thread(
                    storage.client_data.has_permission, module
                )
                if not has_access:
                    page.views.append(
                        ErrorPage(
                            page,
                            "modules",
                            module,
                            screen,
                            f"Access denied to module: {module}",
                        ).build()
                    )
                else:
                    storage.module_history.add(module, screen, record_id)
                    await asyncio.to_thread(
                        modules.build, module, screen, record_id
                    )
        elif page.route.startswith("/modals/"):
            modal, screen, record_id = modals.parse_route(page.route)
            if modal is None:
                page.views.append(
                    ErrorPage(page, "modals", "unknown", "index", "Not found").build()
                )
            else:
                await asyncio.to_thread(modals.build, modal, screen, record_id)
        else:
            page.run_task(page.push_route, "/login")
            return

        loading_overlay.hide()
        page.update()

    def view_pop(view):
        """Handle back navigation"""
        page.views.pop()
        if len(page.views) > 0:
            top_view = page.views[-1]
            page.run_task(page.push_route, top_view.route)
        else:
            page.run_task(page.push_route, "/home")

    def page_resized(e: ft.ControlEvent):
        print("New page size:", page.width, page.height)
        print("New window size:", page.window.width, page.window.height)
        page.window.width = max(page.window.width, 400)
        page.window.height = max(page.window.height, 600)

        # Notify all active tables about resize
        if hasattr(page, "data") and isinstance(page.data, dict):
            active_tables = page.data.get("active_tables", [])
            # Filter out destroyed/invalid tables
            valid_tables = [
                table
                for table in active_tables
                if hasattr(table, "on_page_resize") and hasattr(table, "page")
            ]
            page.data["active_tables"] = valid_tables

            for table in valid_tables:
                try:
                    table.on_page_resize()
                except Exception as e:
                    print(f"Error resizing table: {e}")

        page.update()

    page.on_route_change = route_change
    page.on_view_pop = view_pop
    page.on_resized = page_resized

    async def _push_route_safe(route: str):
        # page.push_route() round-trips to the client (_invoke_method) with
        # NO timeout on the Python side - if the client hasn't fully
        # mounted its method-call listener yet (same class of race as the
        # documented #648 SharedPreferences issue, just a different
        # client-side channel), this can hang forever with nothing left to
        # print. Bound it with the same fail-fast-and-retry helper used for
        # SharedPreferences, and surface a visible, actionable failure
        # instead of an indefinite silent freeze.
        try:
            await sp_call_with_retry(
                page.push_route, route, retries=2, delay=0.3, per_call_timeout=3.0
            )
        except Exception as e:
            print(f"push_route({route!r}) failed after retries: {e}")
            splash.set_progress(
                1, f"Navigation to {route} failed - tap Reload Library to retry"
            )
            splash.show_reload_button(lambda e: page.run_task(_reload_library))

    async def _boot_navigate():
        # DEFAULT_SERVER_URL doubles as the "never configured" sentinel: a
        # never-configured install has nothing persisted, so server_url.get()
        # falls back to it. It's now the containerized deployment's real
        # backend address (see repository/server_url.py), so this branch
        # mainly matters for a genuinely fresh install of some *other*
        # deployment target (native desktop, etc.) where DEFAULT_SERVER_URL
        # doesn't resolve - force the user to set a real server URL first
        # there, instead of throwing a connection error against it or
        # letting them sit on a login screen that can never succeed.
        server_url = storage.server_url.get()
        if server_url == DEFAULT_SERVER_URL:
            # Could be a genuinely unconfigured install, or the #648
            # SharedPreferences hot-reload race (see storage_compat.py)
            # silently failing to load the real persisted value in time -
            # a hot-reloaded `main()` run sees this far more often than a
            # cold process start. Give the read one more explicit try
            # before concluding the server was never configured; a real
            # value on disk resolves on the retry, a genuinely unconfigured
            # install just re-defaults and proceeds as before.
            await storage.server_url.load()
            server_url = storage.server_url.get()

        if server_url == DEFAULT_SERVER_URL:
            await _push_route_safe("/server_config")
        elif storage.client_data.is_active():
            await _push_route_safe("/home")
        else:
            await _push_route_safe("/login")

    async def _reload_library(e=None):
        # Dev-only recovery button (see SplashScreen.show_reload_button):
        # a hot-reloaded `flet run -r` session can end up with a stale
        # module cache or a navigation that silently never fires after a
        # code edit. Drop every preloaded pages.modules/pages.modals
        # module from sys.modules and the ModuleLoader cache, preload
        # fresh, and retry the boot navigation - without needing a full
        # process restart.
        nonlocal storage
        ModuleLoader.reset_cache()

        # Retrying reads on the SAME SharedPreferences service instance
        # doesn't help if that specific instance's client-side listener
        # never mounted - storage_compat.py documents this as a known
        # upstream Flet bug where the call "can never succeed no matter
        # how long we wait" once a connection is in that state. Drop the
        # old service instance(s) and register a fresh one, giving the
        # client the same mount grace period as a cold boot, instead of
        # retrying a connection that's provably stuck.
        splash.set_progress(None, "Reconnecting to shared preferences...")
        page.services[:] = [
            s for s in page.services if not isinstance(s, ft.SharedPreferences)
        ]
        storage = Storage(page)
        await asyncio.sleep(0.5)
        await storage.load_persistent()

        _preload_all()
        await _boot_navigate()

    splash.show_reload_button(lambda e: page.run_task(_reload_library))
    await _boot_navigate()


if __name__ == "__main__":
    # Guarded so `asgi.py` (the containerized deployment's entrypoint, see
    # its docstring) can `from main import main` without this launching a
    # second, competing Flet server via the socket-based CLI path -
    # `flet run` / `python main.py` still hit this normally.
    ft.run(main)
