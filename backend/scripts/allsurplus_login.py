"""One-time AllSurplus login capture.

Opens a headed Chromium browser, lets you log in interactively, then dumps
the resulting cookies + localStorage to backend/scripts/secrets/allsurplus_state.json.

Run from repo root:
    python3 backend/scripts/allsurplus_login.py

Then ship the file to the Proxmox runner:
    scp -i ~/.ssh/id_arcanos backend/scripts/secrets/allsurplus_state.json \\
        root@100.68.229.127:/opt/scraper-runner/.secrets/allsurplus_state.json

Cookies typically last ~30 days on AllSurplus. Re-run this script + re-ship
when the freshness checker alerts.
"""
import os
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent / "secrets" / "allsurplus_state.json"
OUT.parent.mkdir(exist_ok=True)


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: playwright not installed. Run: pip3 install --user playwright", file=sys.stderr)
        return 1

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=False)
        except Exception as exc:
            print(f"ERROR launching Chromium: {exc}", file=sys.stderr)
            print("Try: python3 -m playwright install chromium", file=sys.stderr)
            return 1

        ctx = browser.new_context()
        page = ctx.new_page()
        page.goto("https://www.allsurplus.com/en/login", wait_until="domcontentloaded")

        print()
        print("=" * 60)
        print("  AllSurplus Login Capture")
        print("=" * 60)
        print("  1. Log in via the browser window that just opened.")
        print("  2. Navigate to your account page once to confirm")
        print("     you're logged in (e.g. click the account icon).")
        print("  3. Come back here and press ENTER.")
        print("=" * 60)
        print()
        try:
            input("Press ENTER once you're logged in (Ctrl-C to abort): ")
        except KeyboardInterrupt:
            print("\nAborted; no state saved.")
            browser.close()
            return 130

        state = ctx.storage_state()
        OUT.write_text(__import__("json").dumps(state, indent=2))
        cookie_count = len(state.get("cookies", []))
        ls_origins = len(state.get("origins", []))
        print(f"\nSaved storage state: {cookie_count} cookies, {ls_origins} origins.")
        print(f"  -> {OUT}")
        print()
        print("Next: ship to Proxmox runner with:")
        print(f"  scp -i ~/.ssh/id_arcanos {OUT} root@100.68.229.127:/opt/scraper-runner/.secrets/allsurplus_state.json")

        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
