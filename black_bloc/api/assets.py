from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from .. import __version__

NO_STORE = "no-store"
REVALIDATE = "no-cache"
DIGEST_CHARS = 12
ASSET_URL = re.compile(r'(?P<attr>href|src)="(?P<url>/assets/[^"?#]+)"')


def build_id(root: Path) -> str:
    """`<version>-<digest>` over every byte the site serves."""
    digest = hashlib.sha256(__version__.encode("utf-8"))
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return f"{__version__}-{digest.hexdigest()[:DIGEST_CHARS]}"


def stamp(html: str, build: str) -> str:
    return ASSET_URL.sub(lambda found: f'{found["attr"]}="{found["url"]}?v={build}"', html)


class SiteFiles(StaticFiles):
    """The dashboard's static mount: stamped, never-stored HTML over revalidated assets."""

    def __init__(self, *, directory: Path, build: str) -> None:
        super().__init__(directory=directory, html=True)
        self.build = build

    async def get_response(self, path: str, scope: Any) -> Response:
        response = await super().get_response(path, scope)
        target = getattr(response, "path", None)
        if target is None:
            return response
        if str(target).endswith(".html"):
            text = Path(target).read_text(encoding="utf-8")
            return HTMLResponse(
                stamp(text, self.build),
                status_code=response.status_code,
                headers={"Cache-Control": NO_STORE, "Pragma": "no-cache"},
            )
        response.headers["Cache-Control"] = REVALIDATE
        return response
