"""Convert a Netscape cookies.txt (e.g. from "Get cookies.txt LOCALLY") into
Playwright's storage_state JSON format used by crawl4ai.

Usage:
    python3 backend/scripts/cookies_to_storage_state.py \\
        ~/Downloads/allsurplus.com_cookies.txt

Writes backend/scripts/secrets/allsurplus_state.json.
"""
import json
import sys
from pathlib import Path


def parse_cookies_txt(path: Path) -> list[dict]:
    cookies: list[dict] = []
    for raw in path.read_text().splitlines():
        line = raw.rstrip("\n").rstrip("\r")
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 7:
            continue
        domain, flag, cpath, secure, expires, name, value = parts[:7]
        try:
            expires_int = int(expires)
        except ValueError:
            expires_int = -1
        cookies.append({
            "name": name,
            "value": value,
            "domain": domain,
            "path": cpath,
            "expires": expires_int if expires_int > 0 else -1,
            "httpOnly": False,
            "secure": secure.upper() == "TRUE",
            "sameSite": "Lax",
        })
    return cookies


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: cookies_to_storage_state.py <cookies.txt>", file=sys.stderr)
        return 2

    src = Path(argv[1]).expanduser()
    if not src.exists():
        print(f"ERROR: file not found: {src}", file=sys.stderr)
        return 1

    cookies = parse_cookies_txt(src)
    if not cookies:
        print(f"ERROR: no cookies parsed from {src}", file=sys.stderr)
        return 1

    state = {"cookies": cookies, "origins": []}
    out = Path(__file__).resolve().parent / "secrets" / "allsurplus_state.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(state, indent=2))

    domains = sorted({c["domain"] for c in cookies})
    print(f"Wrote {len(cookies)} cookies across {len(domains)} domain(s) to {out}")
    print("Domains:")
    for d in domains:
        cnt = sum(1 for c in cookies if c["domain"] == d)
        print(f"  {d}  ({cnt})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
