"""Configuracion comun de las pruebas Selenium (modulo sparePart).

Variables de entorno:
  BASE_URL      URL del frontend            (por defecto http://localhost:5173)
  APP_USER      usuario con permisos        (por defecto admin)
  APP_PASSWORD  contrasena de ese usuario   (obligatoria)
  BROWSER       chrome | edge               (por defecto chrome)
  HEADLESS      1 para correr sin ventana   (por defecto 0)
"""
import os
from pathlib import Path

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

BASE_URL = os.getenv("BASE_URL", "http://localhost:5173").rstrip("/")
APP_USER = os.getenv("APP_USER", "admin")
APP_PASSWORD = os.getenv("APP_PASSWORD", "")
BROWSER = os.getenv("BROWSER", "chrome").lower()
HEADLESS = os.getenv("HEADLESS", "0") == "1"
CAPTURAS = Path(__file__).parent / "capturas"
TIMEOUT = 15


def _crear_driver():
    if BROWSER == "edge":
        opciones = webdriver.EdgeOptions()
        if HEADLESS:
            opciones.add_argument("--headless=new")
        opciones.add_argument("--window-size=1400,900")
        return webdriver.Edge(options=opciones)
    opciones = webdriver.ChromeOptions()
    if HEADLESS:
        opciones.add_argument("--headless=new")
    opciones.add_argument("--window-size=1400,900")
    opciones.add_argument("--disable-gpu")
    return webdriver.Chrome(options=opciones)


@pytest.fixture
def driver():
    if not APP_PASSWORD:
        pytest.skip("Define la variable de entorno APP_PASSWORD")
    CAPTURAS.mkdir(exist_ok=True)
    d = _crear_driver()
    d.implicitly_wait(0)
    yield d
    d.quit()


@pytest.fixture
def esperar(driver):
    return WebDriverWait(driver, TIMEOUT)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Si una prueba falla, guarda una captura para el reporte."""
    resultado = yield
    reporte = resultado.get_result()
    if reporte.when == "call" and reporte.failed:
        d = item.funcargs.get("driver")
        if d is not None:
            CAPTURAS.mkdir(exist_ok=True)
            d.save_screenshot(str(CAPTURAS / f"FALLO_{item.name}.png"))