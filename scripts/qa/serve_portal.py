"""Serve a local portal under its project base path with gzip for browser QA."""

import argparse
import gzip
import io
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8893)
    args = parser.parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        parser.error("Portal root must exist")
    prefix = "/awesome-gaussian-splatting/"

    class Handler(SimpleHTTPRequestHandler):
        def do_GET(self):
            if urlsplit(self.path).path == "/":
                self.send_response(302)
                self.send_header("Location", prefix)
                self.end_headers()
                return
            if not urlsplit(self.path).path.startswith(prefix):
                self.send_error(404)
                return
            super().do_GET()

        def translate_path(self, path):
            if urlsplit(path).path.startswith(prefix):
                path = path[len(prefix) - 1 :]
            return super().translate_path(path)

        def send_head(self):
            path = Path(self.translate_path(self.path))
            if path.is_dir():
                path = path / "index.html"
            if (
                path.is_file()
                and path.suffix in {".html", ".json", ".js", ".css"}
                and "gzip" in self.headers.get("Accept-Encoding", "")
            ):
                payload = gzip.compress(path.read_bytes(), mtime=0)
                self.send_response(200)
                self.send_header("Content-Type", self.guess_type(str(path)))
                self.send_header("Content-Encoding", "gzip")
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                return io.BytesIO(payload)
            return super().send_head()

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", args.port), partial(Handler, directory=str(root)))
    print(f"Serving {root} at http://127.0.0.1:{args.port}{prefix}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
