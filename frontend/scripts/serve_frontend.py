"""Serve the built frontend with an index fallback for vehicle routes."""

from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class SpaHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, directory: str | None = None, **kwargs):
        super().__init__(*args, directory=directory, **kwargs)

    def do_GET(self) -> None:
        if self.path.startswith("/vehicle/"):
            self.path = "/index.html"
        super().do_GET()


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the built frontend with SPA fallback.")
    parser.add_argument("build_dir")
    parser.add_argument("port", type=int)
    args = parser.parse_args()

    build_dir = Path(args.build_dir).resolve()
    handler = partial(SpaHandler, directory=str(build_dir))
    with ThreadingHTTPServer(("0.0.0.0", args.port), handler) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
