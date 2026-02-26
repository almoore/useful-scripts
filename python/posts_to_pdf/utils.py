"""Shared utilities: debug output and browser cookie loading."""

try:
    import browser_cookie3
except ImportError:
    browser_cookie3 = None

DEBUG = False


def set_debug(enabled):
    """Set the module-level DEBUG flag."""
    global DEBUG
    DEBUG = enabled


def debug_print(*args):
    """Print debug messages when DEBUG mode is enabled."""
    if DEBUG:
        print("[DEBUG]", *args)


def _load_browser_cookies(domain, browser_name=None):
    """Load cookies for a domain from the user's browser.

    Args:
        domain: Domain to extract cookies for (e.g. ".substack.com").
        browser_name: Specific browser ("chrome", "firefox", "safari", "edge").
                      If None, tries all browsers in order.

    Returns:
        A cookie jar, or None if extraction failed.
    """
    if not browser_cookie3:
        print("Error: browser-cookie3 is not installed. "
              "Install with: pip install browser-cookie3")
        return None

    browsers = {
        "chrome": browser_cookie3.chrome,
        "firefox": browser_cookie3.firefox,
        "safari": browser_cookie3.safari,
        "edge": browser_cookie3.edge,
    }

    if browser_name:
        names = [browser_name]
    else:
        names = ["chrome", "firefox", "safari", "edge"]

    for name in names:
        loader = browsers.get(name)
        if not loader:
            continue
        try:
            cj = loader(domain_name=domain)
            cookie_count = sum(1 for c in cj if domain in (c.domain or ""))
            if cookie_count > 0:
                print(f"Loaded {cookie_count} cookies from {name} for {domain}")
                return cj
        except Exception as e:
            if browser_name:
                print(f"Warning: Could not load cookies from {name}: {e}")
            # Silently skip when auto-detecting

    if not browser_name:
        print("Warning: Could not find Substack cookies in any browser. "
              "Make sure you are logged in to Substack in your browser.")
    return None
