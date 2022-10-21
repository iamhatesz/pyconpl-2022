from threading import Thread
from time import sleep

import requests
from flask import Flask
from werkzeug.serving import BaseWSGIServer, make_server


class ThreadedFlaskServer:
    def __init__(self, app: Flask, host: str = "127.0.0.1", port: int = 5000):
        self._app = app
        self._host = host
        self._port = port
        self._server: BaseWSGIServer | None = None
        self._thread: Thread | None = None

    @property
    def url(self) -> str:
        return f"http://{self._host}:{self._port}"

    def __enter__(self) -> "ThreadedFlaskServer":
        self._thread = Thread(target=self._serve_app)
        self._thread.start()
        self._await_for_server_start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._server.shutdown()
        self._thread.join()

    def _serve_app(self):
        self._app.route("/healthcheck")(lambda: "OK")
        self._server = make_server(self._host, self._port, self._app, threaded=False)
        self._server.serve_forever()

    def _await_for_server_start(self):
        while True:
            if not self._thread.is_alive():
                continue
            if self._port is None:
                continue
            try:
                resp = requests.get(f"{self.url}/healthcheck")
                resp.raise_for_status()
                break
            except (ConnectionError, requests.ConnectionError, requests.HTTPError):
                sleep(0.1)
