import logging
from collections import deque
from time import sleep
from typing import Callable

import pytest
import trio
from flask import Flask, jsonify
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.bidi.cdp import CdpSession
from selenium.webdriver.common.by import By
from selenium.webdriver.common.devtools.v106 import network
from selenium.webdriver.common.devtools.v106.network import (
    RequestWillBeSent,
    ResponseReceived,
    LoadingFailed,
    LoadingFinished,
)

from driver import create_driver
from server import ThreadedFlaskServer

LOG = logging.getLogger(__name__)


@pytest.fixture
def application() -> ThreadedFlaskServer:
    app = Flask(__name__)
    app.config.update({"TESTING": True})

    @app.route("/")
    def index():
        return """
        <html>
            <head>
                <title>Results page</title>
            </head>
            <body>
                <a id="get-results">Get results</a>
                <div id="results"></div>

                <script type="text/javascript">
                    const button = document.getElementById("get-results");
                    const results = document.getElementById("results");
                    button.addEventListener("click", (event) => {
                        fetch(document.location.href + "results")
                            .then((response) => response.json())
                            .then((data) => results.innerText = data["data"]);
                    });
                </script>
            </body>
        </html>
        """

    @app.route("/results")
    def results():
        sleep(5)
        return jsonify({"data": "some very important data"})

    with ThreadedFlaskServer(app) as server:
        yield server


@pytest.fixture
def driver() -> WebDriver:
    with create_driver(headless=True) as _driver:
        yield _driver


async def execute_and_await(
    driver: WebDriver,
    action: Callable[[], None],
    timeout: float = 10.0,
    num_checks: int = 10,
    window_length: float = 1.0,
):
    requests: dict[str, bool] = {}

    async def request_tracker(
        session: CdpSession,
        task_status: "trio._core._run._TaskStatusIgnored" = trio.TASK_STATUS_IGNORED,
    ):
        task_status.started()
        async for event in session.listen(
            RequestWillBeSent, ResponseReceived, LoadingFailed, LoadingFinished
        ):
            match event:
                case RequestWillBeSent(request_id=request_id, request=request):
                    LOG.debug("New request:", request)
                    requests[request_id] = True
                case LoadingFailed(request_id=request_id) | LoadingFinished(
                    request_id=request_id
                ):
                    LOG.debug("Request finalized:", request_id)
                    requests[request_id] = False

    ready = trio.Event()

    async def await_pending_requests(
        task_status: "trio._core._run._TaskStatusIgnored" = trio.TASK_STATUS_IGNORED,
    ):
        checks = deque(range(num_checks), maxlen=num_checks)
        check_interval = window_length // max(num_checks, 1)
        task_status.started()
        while True:
            num_pending_requests = sum(requests.values())
            checks.append(num_pending_requests)
            status = sum(checks) == 0
            if status:
                ready.set()
                break
            await trio.sleep(check_interval)

    async with driver.bidi_connection() as bidi_session:
        session: CdpSession = bidi_session.session
        await session.execute(network.enable())
        async with trio.open_nursery() as nursery:
            await nursery.start(request_tracker, session)
            await nursery.start(await_pending_requests)
            action()
            with trio.move_on_after(timeout) as cancel_scope:
                await ready.wait()
            if cancel_scope.cancelled_caught:
                LOG.debug("Timeout waiting for the pending requests.")
            nursery.cancel_scope.cancel()


def test_results_are_displayed_after_click_button(
    application: ThreadedFlaskServer, driver: WebDriver
):
    driver.get(application.url)
    button = driver.find_element(By.ID, "get-results")
    results = driver.find_element(By.ID, "results")
    trio.run(execute_and_await, driver, button.click)
    assert results.text == "some very important data"
