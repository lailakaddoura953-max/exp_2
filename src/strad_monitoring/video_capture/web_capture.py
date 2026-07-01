"""
Web-Based Screenshot Capture - Capture full-window screenshots from Axis camera
web viewer pages using a headless browser.

This replaces direct RTSP frame-grabbing (which does not work reliably against
these Axis encoders - confirmed: browser access fails outright, and VLC only
shows a single corner of the feed for the same RTSP path). Instead, this module
drives a real (headless) browser to the camera's web viewer, authenticates via
a plain HTML login form, waits for the video panel to render, and takes a
full-window screenshot - matching the retrained model, which expects full-window
captures rather than a cropped video-only region.

Known Axis viewer URL patterns (varies by firmware, can change across
upgrades - both are tried in order):
    http://{ip}/camera/index.html          (newer AXIS OS)
    http://{ip}/view/viewer_index.shtml?id=0  (classic VAPIX viewer)

Login form (same across both page versions, per confirmation):
    Plain white box with username and password fields, no browser-native
    HTTP Basic Auth dialog involved.

NOTE ON SELECTORS: The exact `name`/`id` attributes of the username/password
fields and submit control have not been confirmed against a live page yet.
The selectors below are marked TODO and use broad, best-effort matching
(common Axis field names + generic fallbacks) so this can run out of the box,
but they should be verified/tightened once the page is inspected directly.
"""

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    PlaywrightTimeoutError = Exception
    logger.warning("Playwright not available - web-based capture will not work. "
                    "Install with: pip install playwright && playwright install chromium")


# Candidate viewer paths to try, in order. Axis firmware upgrades can change
# which one a given camera serves, so both are attempted per capture.
VIEWER_URL_PATHS = [
    "/camera/index.html",
    "/view/viewer_index.shtml?id=0",
]

# TODO: Confirm exact field selectors once page HTML is inspected.
# Broad best-effort selectors for the plain username/password login form.
USERNAME_SELECTORS = [
    "input[name='username']",
    "input[id='username']",
    "input[name='user']",
    "input[type='text']",
]
PASSWORD_SELECTORS = [
    "input[name='password']",
    "input[id='password']",
    "input[type='password']",
]
SUBMIT_SELECTORS = [
    "button[type='submit']",
    "input[type='submit']",
    "button:has-text('Login')",
    "button:has-text('Log in')",
    "button:has-text('Sign in')",
]


class WebCaptureError(Exception):
    """Exception raised when web-based screenshot capture fails."""
    pass


class WebCapture:
    """
    Capture full-window screenshots from Axis camera web viewer pages.

    Launches a headless browser per capture (safe across orchestrator worker
    threads), navigates to the camera's viewer page (trying known URL
    patterns), logs in via the plain username/password form if present,
    waits for the video panel to stabilize, and takes a full-window
    screenshot.
    """

    def __init__(
        self,
        username: str,
        password: str,
        timeout_seconds: int = 45,
        stabilization_delay_seconds: float = 3.0,
        max_retries: int = 3,
        min_width: int = 640,
        min_height: int = 480,
        viewport_width: int = 1280,
        viewport_height: int = 800,
    ):
        """
        Initialize web capture parameters.

        Args:
            username: Login username for the camera web viewer
            password: Login password for the camera web viewer
            timeout_seconds: Max time to wait for page navigation/login (default 45)
            stabilization_delay_seconds: Wait after page load for video panel to
                render before capturing (default 3.0)
            max_retries: Max retry attempts on failure (default 3)
            min_width: Minimum screenshot width validation (default 640)
            min_height: Minimum screenshot height validation (default 480)
            viewport_width: Browser viewport width (default 1280)
            viewport_height: Browser viewport height (default 800)
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError(
                "Playwright not installed. Run:\n"
                "  pip install playwright\n"
                "  playwright install chromium"
            )

        self.username = username
        self.password = password
        self.timeout_seconds = timeout_seconds
        self.stabilization_delay_seconds = stabilization_delay_seconds
        self.max_retries = max_retries
        self.min_width = min_width
        self.min_height = min_height
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height

        logger.info(
            f"WebCapture initialized: timeout={timeout_seconds}s, "
            f"stabilization={stabilization_delay_seconds}s, retries={max_retries}, "
            f"viewport={viewport_width}x{viewport_height}"
        )

    def capture_frame(
        self,
        ip_address: str,
        strad_id: str,
        snapshot_dir: str
    ) -> Tuple[Optional[str], bool]:
        """
        Capture a full-window screenshot of the camera viewer page at ip_address.

        Args:
            ip_address: IP address of the camera (e.g., "192.168.1.100")
            strad_id: Strad ID for filename (e.g., "SC001")
            snapshot_dir: Directory to save screenshot

        Returns:
            Tuple of (filepath, success). filepath is None on failure.

        Filename Format:
            SC{strad_id}_{YYYYMMDD}_{HHMMSS}.jpg
        """
        logger.info(f"Starting web capture for {strad_id} at {ip_address}")
        Path(snapshot_dir).mkdir(parents=True, exist_ok=True)

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug(f"Capture attempt {attempt}/{self.max_retries}")
                filepath = self._attempt_capture(ip_address, strad_id, snapshot_dir)
                if filepath:
                    logger.info(f"✓ Web capture succeeded: {filepath}")
                    return (filepath, True)
                logger.warning(f"Attempt {attempt}: capture returned no file")
            except Exception as e:
                logger.warning(f"Attempt {attempt}: web capture failed: {e}")

            if attempt < self.max_retries:
                time.sleep(1)

        logger.error(f"All {self.max_retries} web capture attempts failed for {strad_id}")
        return (None, False)

    def _attempt_capture(
        self,
        ip_address: str,
        strad_id: str,
        snapshot_dir: str
    ) -> Optional[str]:
        """
        Single capture attempt: launch browser, navigate, login, screenshot, close.

        Browser is launched and closed within this call so it stays confined
        to whatever thread invoked it (APScheduler worker thread, etc.) -
        Playwright's sync API is not safe to share across threads.
        """
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                context = browser.new_context(
                    viewport={"width": self.viewport_width, "height": self.viewport_height},
                    ignore_https_errors=True,
                    # Harmless if the page doesn't actually use HTTP Basic Auth;
                    # answers it automatically before the page renders if it does.
                    http_credentials={"username": self.username, "password": self.password},
                )
                page = context.new_page()
                page.set_default_timeout(self.timeout_seconds * 1000)

                if not self._navigate_to_viewer(page, ip_address):
                    raise WebCaptureError(
                        f"Could not reach any known viewer URL for {ip_address}"
                    )

                self._login_if_needed(page)

                # Let the video panel render/stabilize before capturing
                time.sleep(self.stabilization_delay_seconds)

                filepath = self._save_screenshot(page, strad_id, snapshot_dir)

                if not self._validate_screenshot(filepath):
                    if filepath and Path(filepath).exists():
                        Path(filepath).unlink()
                    return None

                return filepath
            finally:
                browser.close()

    def _navigate_to_viewer(self, page, ip_address: str) -> bool:
        """
        Try each known viewer URL pattern until one loads successfully.

        Firmware upgrades can change which path a given camera serves, so
        both patterns are attempted rather than assuming one.
        """
        for path in VIEWER_URL_PATHS:
            url = f"http://{ip_address}{path}"
            try:
                logger.debug(f"Trying viewer URL: {url}")
                response = page.goto(url, wait_until="domcontentloaded")
                if response is not None and response.ok:
                    logger.debug(f"Loaded viewer page: {url}")
                    return True
                logger.debug(f"Non-OK response for {url}: {response.status if response else 'no response'}")
            except PlaywrightTimeoutError:
                logger.debug(f"Timeout loading {url}")
            except Exception as e:
                logger.debug(f"Failed to load {url}: {e}")

        return False

    def _login_if_needed(self, page) -> None:
        """
        Fill and submit the username/password login form if present.

        The login page is a plain HTML form (not a browser-native Basic Auth
        dialog), so it's just a matter of finding the input fields and submit
        control. Selectors are best-effort (see module TODO) since exact
        field attributes haven't been confirmed against a live page.
        """
        username_field = self._find_first(page, USERNAME_SELECTORS)
        password_field = self._find_first(page, PASSWORD_SELECTORS)

        if not username_field or not password_field:
            logger.debug("No login form detected - assuming already authenticated or not required")
            return

        logger.info("Login form detected - submitting credentials")
        username_field.fill(self.username)
        password_field.fill(self.password)

        submit_control = self._find_first(page, SUBMIT_SELECTORS)
        if submit_control:
            submit_control.click()
        else:
            # Fallback: submit by pressing Enter in the password field
            password_field.press("Enter")

        try:
            page.wait_for_load_state("domcontentloaded", timeout=self.timeout_seconds * 1000)
        except PlaywrightTimeoutError:
            logger.debug("No navigation detected after login submit (may be AJAX-based login)")

    def _find_first(self, page, selectors):
        """Return the first matching, visible locator from a list of selectors, or None."""
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if locator.count() > 0 and locator.is_visible():
                    return locator
            except Exception:
                continue
        return None

    def _save_screenshot(
        self,
        page,
        strad_id: str,
        snapshot_dir: str
    ) -> Optional[str]:
        """
        Save a full-window (viewport) screenshot to JPEG with timestamp.

        Filename format: SC{strad_id}_{YYYYMMDD}_{HHMMSS}.jpg
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            normalized_id = strad_id[2:] if strad_id.upper().startswith("SC") else strad_id
            normalized_id = normalized_id.zfill(3)

            filename = f"SC{normalized_id}_{timestamp}.jpg"
            filepath = str(Path(snapshot_dir) / filename)

            # full_page=False: capture the viewport (the "full window" the model
            # was trained on), not the entire scrollable page content.
            page.screenshot(path=filepath, full_page=False, type="jpeg", quality=85)
            logger.debug(f"Screenshot saved: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to save screenshot: {e}", exc_info=True)
            return None

    def _validate_screenshot(self, filepath: Optional[str]) -> bool:
        """Validate the saved screenshot exists, is non-empty, and meets minimum dimensions."""
        if not filepath:
            return False

        path = Path(filepath)
        if not path.exists() or path.stat().st_size == 0:
            logger.warning(f"Screenshot missing or empty: {filepath}")
            return False

        try:
            from PIL import Image
            with Image.open(filepath) as img:
                width, height = img.size
        except Exception as e:
            logger.warning(f"Could not read screenshot for validation: {e}")
            return False

        if width < self.min_width or height < self.min_height:
            logger.warning(
                f"Screenshot dimensions too small: {width}x{height} "
                f"(minimum: {self.min_width}x{self.min_height})"
            )
            return False

        return True

    def summary(self) -> str:
        """Get a summary of web capture configuration."""
        return (
            f"Web Capture Configuration:\n"
            f"  Timeout: {self.timeout_seconds}s\n"
            f"  Stabilization delay: {self.stabilization_delay_seconds}s\n"
            f"  Max retries: {self.max_retries}\n"
            f"  Min screenshot size: {self.min_width}x{self.min_height}\n"
            f"  Viewport: {self.viewport_width}x{self.viewport_height}\n"
            f"  Viewer URL patterns tried: {VIEWER_URL_PATHS}"
        )
