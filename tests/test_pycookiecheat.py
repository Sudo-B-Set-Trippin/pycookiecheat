"""test_pycookiecheat.py :: Tests for pycookiecheat module."""

import sys
import time
import typing as t
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import URLError
from uuid import uuid4

import pytest

from playwright.sync_api import sync_playwright
from pycookiecheat import chrome_cookies


@pytest.fixture(scope="module")
def ci_setup() -> None:
    """Set up Chrome's cookies file and directory.

    Unfortunately, at least on MacOS 11, I haven't found a way to do this using
    a temporary directory or without accessing my actual keyring and profile.

    Things I've tried:
        - Use a temp directory for user-data-dir instead of actual Chrome
          profile
            - Seems not to work because the password is not correct for the
              profile.
            - Chrome generates a random password if one is not found for the
              profile, but this doesn't get added to Keychain and I haven't
              found a way to figure out what it's using for a particulary run

    Other notes:
        - Seems to require the "profile-directory" option instead of usign the
          path to `Default` directly in user-data-dir
        - Seems to require a `max-age` for the cookie to last session to
          session

    https://chromium.googlesource.com/chromium/src/+/refs/heads/master/components/os_crypt/keychain_password_mac.mm
    """
    with TemporaryDirectory() as cookies_home, sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            cookies_home,
            headless=False,
            ignore_default_args=[
                "--use-mock-keychain",
            ],
        )
        page = browser.new_page()
        page.goto("https://n8henrie.com")
        browser.add_cookies(
            [
                {
                    "name": "test_pycookiecheat",
                    "value": "It worked!",
                    "domain": "n8henrie.com",
                    "path": "/",
                    "expires": int(time.time()) + 300,
                }
            ]
        )
        browser.close()
        cookie_file = Path(cookies_home) / "Default" / "Cookies"
        yield cookie_file


def test_raises_on_empty() -> None:
    """Ensure that `chrome_cookies()` raises."""
    with pytest.raises(TypeError):
        chrome_cookies()  # type: ignore


def test_raises_without_scheme() -> None:
    """Ensure that `chrome_cookies("domain.com")` raises.

    The domain must specify a scheme (http or https).

    """
    with pytest.raises(URLError):
        chrome_cookies("n8henrie.com")


def test_no_cookies(ci_setup: t.Callable) -> None:
    """Ensure that no cookies are returned for a fake url."""
    never_been_here = "http://{0}.com".format(uuid4())
    empty_dict = chrome_cookies(never_been_here)
    assert empty_dict == dict()


def test_fake_cookie(ci_setup: t.Callable) -> None:
    """Tests a fake cookie from the website below.

    For this to pass, you'll have to visit the url and put in "TestCookie" and
    "Just_a_test!" to set a temporary cookie with the appropriate values.
    """
    if sys.version_info < (3, 7):
        return
    cookies = chrome_cookies(
        "https://n8henrie.com",
        cookie_file=ci_setup,
        browser="Chromium",
    )
    assert cookies.get("test_pycookiecheat") == "It worked!"


def test_raises_on_wrong_browser() -> None:
    """Passing a browser other than Chrome or Chromium raises ValueError."""
    with pytest.raises(ValueError):
        chrome_cookies("https://n8henrie.com", browser="Safari")
