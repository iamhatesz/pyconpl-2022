import contextlib

from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver


@contextlib.contextmanager
def create_driver(
    headless: bool = True, window_size: tuple[int, int] = (1024, 768)
) -> WebDriver:
    options = webdriver.ChromeOptions()
    options.add_argument("--mute-audio")
    if headless:
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-browser-side-navigation")
        options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)
    driver.set_window_size(*window_size)
    driver.get("about:blank")
    yield driver
    driver.quit()
