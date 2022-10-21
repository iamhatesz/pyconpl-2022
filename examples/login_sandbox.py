import pytest
from selenium.common import TimeoutException
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait

from driver import create_driver


@pytest.fixture
def driver() -> WebDriver:
    with create_driver(headless=False) as _driver:
        yield _driver


@pytest.fixture
def application_url() -> str:
    return "https://alan-sandbox-qa-internal.gatdev.io/login"


def test_user_is_logged_in_after_filling_login_form(
    driver: WebDriver, application_url: str
):
    driver.get(application_url)
    email = driver.find_element(By.XPATH, "//form/div[1]/label/input")
    password = driver.find_element(By.XPATH, "//form/div[2]/label/input")
    submit = driver.find_element(By.XPATH, "//form/button")
    (
        ActionChains(driver)
        .send_keys_to_element(email, "alan@globalapptesting.com")
        .send_keys_to_element(password, "Alan12345!")
        .click(submit)
        .perform()
    )
    try:
        WebDriverWait(driver, timeout=5).until(
            expected_conditions.presence_of_element_located((By.LINK_TEXT, "account")),
            "The user hasn't been logged in/",
        )
    except TimeoutException as e:
        pytest.fail(e.msg)
