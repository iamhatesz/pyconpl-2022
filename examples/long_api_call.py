from time import sleep

import pytest
from flask import Flask, Response, jsonify
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By

from driver import create_driver
from server import ThreadedFlaskServer


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


def test_results_are_displayed_after_click_button(
    application: ThreadedFlaskServer, driver: WebDriver
):
    driver.get(application.url)
    button = driver.find_element(By.ID, "get-results")
    results = driver.find_element(By.ID, "results")
    button.click()
    assert results.text == "some very important data"
