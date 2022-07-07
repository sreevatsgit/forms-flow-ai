"""Utility functions to manage pdf generation using selenium chrome."""

import base64
import json

from flask import current_app, make_response
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from seleniumwire import webdriver
from formsflow_api.utils import CHROME_DRIVER_PATH


def send_devtools(driver, cmd, params=None):
    """Chrome dev tools execution function."""
    resource = "/session/" + driver.session_id + "/chromium/send_command_and_get_result"
    # pylint: disable=protected-access
    url = driver.command_executor._url + resource
    body = json.dumps({"cmd": cmd, "params": params})
    # pylint: disable=protected-access
    response = driver.command_executor._request("POST", url, body)
    if response.get("status"):
        raise Exception(response.get("value"))
    return response.get("value")


def driver_path():
    """Return chrome webreiver path."""
    return CHROME_DRIVER_PATH


# pylint: disable=R1710


def get_pdf_from_html(
    path, chromedriver=driver_path(), p_options=None, wait=None, auth_token=None
):
    """Load url in chrome web driver and print as pdf."""

    def interceptor(request):
        request.headers["Authorization"] = auth_token

    webdriver_options = Options()
    webdriver_options.add_argument("--headless")
    webdriver_options.add_argument("window-size=1920x1080")
    webdriver_options.add_argument("--disable-gpu")
    webdriver_options.add_argument("--no-sandbox")
    webdriver_options.add_argument("--disable-dev-shm-usage")
    webdriver_options.add_argument("--run-all-compositor-stages-before-draw")

    driver = webdriver.Chrome(chromedriver, options=webdriver_options)
    driver.set_window_size(1920, 1080)

    if auth_token is not None:
        driver.request_interceptor = interceptor
    driver.get(path)

    try:
        if wait is not None:
            delay = 100  # seconds
            elem_loc = EC.presence_of_element_located((By.CLASS_NAME, wait))
            WebDriverWait(driver, delay).until(elem_loc)
        calculated_print_options = {
            "landscape": False,
            "displayHeaderFooter": False,
            "printBackground": True,
            "preferCSSPageSize": True,
        }
        if p_options is not None:
            calculated_print_options.update(p_options)
        result = send_devtools(driver, "Page.printToPDF", calculated_print_options)
        driver.quit()
        return base64.b64decode(result["data"])

    except TimeoutException as err:
        current_app.logger.warning(err)


def pdf_response(result, file_name="Pdf.pdf"):
    """Render pdf response from html content."""
    response = make_response(result)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = "inline; filename=" + file_name
    return response


def save_pdf_local(result, file_name="Pdf.pdf"):
    """Save html content as pdf response."""
    with open(file_name, "wb") as file:
        file.write(result)