"""Pruebas de interfaz Selenium del modulo Repuestos que sería sparePart

Requisitos: MySQL, backend (:8000) y frontend (:5173) corriendo, y un usuario
con permisos spare_parts:*

Ejecucion:
  $env:APP_PASSWORD="12345678"
  pytest selenium_tests -v --junitxml=ui.xml
"""
import time

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC

from conftest import APP_PASSWORD, APP_USER, BASE_URL, CAPTURAS

DIALOGO = "//*[@role='dialog']"


# ----------------------------------------------------------------- utilidades
def capturar(driver, nombre):
    CAPTURAS.mkdir(exist_ok=True)
    driver.save_screenshot(str(CAPTURAS / f"{nombre}.png"))


def campo(driver, etiqueta):
    """Devuelve el input asociado a una etiqueta (label) del modal."""
    label = driver.find_element(
        By.XPATH, f"{DIALOGO}//label[contains(normalize-space(.), '{etiqueta}')]"
    )
    return driver.find_element(By.ID, label.get_attribute("for"))


def escribir(driver, etiqueta, valor):
    el = campo(driver, etiqueta)
    el.send_keys(Keys.CONTROL, "a")
    el.send_keys(str(valor))


def boton_dialogo(driver, esperar, texto):
    return esperar.until(
        EC.element_to_be_clickable(
            (By.XPATH, f"{DIALOGO}//button[normalize-space()='{texto}']")
        )
    )


def fila(nombre):
    return (By.XPATH, f"//tr[td[normalize-space()='{nombre}']]")


def iniciar_sesion(driver, esperar, usuario=APP_USER, clave=APP_PASSWORD):
    driver.get(f"{BASE_URL}/login")
    esperar.until(EC.visibility_of_element_located((By.XPATH, "//label[contains(.,'Usuario')]")))
    for etiqueta, valor in (("Usuario", usuario), ("Contraseña", clave)):
        label = driver.find_element(By.XPATH, f"//label[contains(normalize-space(.), '{etiqueta}')]")
        driver.find_element(By.ID, label.get_attribute("for")).send_keys(valor)
    driver.find_element(By.XPATH, "//button[normalize-space()='Iniciar sesión']").click()


def ir_a_repuestos(driver, esperar):
    esperar.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(.,'Repuestos')]"))).click()
    esperar.until(EC.visibility_of_element_located((By.XPATH, "//h1[normalize-space()='Repuestos'] | //h2[normalize-space()='Repuestos'] | //h3[normalize-space()='Repuestos']")))


def abrir_formulario_nuevo(driver, esperar):
    esperar.until(EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Nuevo repuesto']"))).click()
    esperar.until(EC.visibility_of_element_located((By.XPATH, f"{DIALOGO}//label[contains(.,'Marca')]")))


def crear_repuesto(driver, esperar, nombre, marca="Samsung", parte="QA-001", original=False, stock=5):
    abrir_formulario_nuevo(driver, esperar)
    escribir(driver, "Nombre", nombre)
    escribir(driver, "Marca", marca)
    escribir(driver, "Número de parte", parte)
    if original:
        driver.find_element(By.XPATH, f"{DIALOGO}//label[contains(.,'Repuesto original')]").click()
    escribir(driver, "Stock (unidades)", stock)
    boton_dialogo(driver, esperar, "Guardar").click()
    esperar.until(EC.presence_of_element_located(fila(nombre)))


def eliminar_repuesto(driver, esperar, nombre):
    esperar.until(EC.element_to_be_clickable(
        (By.XPATH, f"//tr[td[normalize-space()='{nombre}']]//button[normalize-space()='Eliminar']"))).click()
    boton_dialogo(driver, esperar, "Eliminar").click()
    esperar.until(EC.invisibility_of_element_located(fila(nombre)))


@pytest.fixture
def sesion(driver, esperar):
    """Inicia sesion y deja la pagina en Repuestos."""
    iniciar_sesion(driver, esperar)
    ir_a_repuestos(driver, esperar)
    return driver


@pytest.fixture
def nombre_unico():
    return f"Tornillo QA {int(time.time() * 1000)}"


# --------------------------------------------------------------------- pruebas
def test_sel01_acceso_al_modulo_repuestos(sesion, esperar):
    """Tras iniciar sesion se puede entrar a Repuestos y se ve la tabla y el boton Nuevo."""
    assert "/spareParts" in sesion.current_url
    esperar.until(EC.visibility_of_element_located((By.XPATH, "//button[normalize-space()='Nuevo repuesto']")))
    for columna in ("Nombre", "Marca", "Número de parte", "Tipo", "Stock (unidades)", "Acciones"):
        esperar.until(EC.presence_of_element_located((By.XPATH, f"//th[normalize-space()='{columna}']")), f"Falta la columna {columna}")
    capturar(sesion, "sel01_modulo_repuestos")


def test_sel02_crear_repuesto_aparece_en_la_tabla(sesion, esperar, nombre_unico):
    """Crear un repuesto con datos validos lo muestra en la tabla como Alternativo."""
    try:
        crear_repuesto(sesion, esperar, nombre_unico, marca="Samsung", parte="QA-002", stock=7)
        celdas = sesion.find_element(*fila(nombre_unico)).text
        assert "Samsung" in celdas and "QA-002" in celdas
        assert "Alternativo" in celdas and "7" in celdas
        capturar(sesion, "sel02_repuesto_creado")
    finally:
        eliminar_repuesto(sesion, esperar, nombre_unico)


def test_sel03_formulario_vacio_muestra_validaciones(sesion, esperar):
    """Guardar sin datos muestra los mensajes de validacion y no cierra el modal."""
    abrir_formulario_nuevo(sesion, esperar)
    boton_dialogo(sesion, esperar, "Guardar").click()
    for mensaje in ("Ingresa el nombre del repuesto", "Ingresa la marca", "Ingresa el número de parte"):
        esperar.until(EC.visibility_of_element_located((By.XPATH, f"{DIALOGO}//*[contains(.,'{mensaje}')]")))
    capturar(sesion, "sel03_validaciones")
    boton_dialogo(sesion, esperar, "Cancelar").click()


def test_sel04_editar_stock_de_un_repuesto(sesion, esperar, nombre_unico):
    """Editar un repuesto actualiza el stock mostrado en la tabla."""
    crear_repuesto(sesion, esperar, nombre_unico, parte="QA-004", stock=3)
    try:
        sesion.find_element(
            By.XPATH, f"//tr[td[normalize-space()='{nombre_unico}']]//button[normalize-space()='Editar']"
        ).click()
        esperar.until(EC.visibility_of_element_located((By.XPATH, f"{DIALOGO}//*[contains(.,'Editar repuesto')]")))
        escribir(sesion, "Stock (unidades)", 25)
        boton_dialogo(sesion, esperar, "Guardar").click()
        esperar.until(EC.text_to_be_present_in_element(fila(nombre_unico), "25"))
        assert "25" in sesion.find_element(*fila(nombre_unico)).text
        capturar(sesion, "sel04_repuesto_editado")
    finally:
        eliminar_repuesto(sesion, esperar, nombre_unico)


def test_sel05_eliminar_repuesto_lo_quita_de_la_tabla(sesion, esperar, nombre_unico):
    """Confirmar la eliminacion hace desaparecer el repuesto de la lista."""
    crear_repuesto(sesion, esperar, nombre_unico, parte="QA-005")
    esperar.until(EC.element_to_be_clickable(
        (By.XPATH, f"//tr[td[normalize-space()='{nombre_unico}']]//button[normalize-space()='Eliminar']"))).click()
    esperar.until(EC.visibility_of_element_located((By.XPATH, f"{DIALOGO}//*[contains(.,'Eliminar repuesto')]")))
    capturar(sesion, "sel05_confirmar_eliminacion")
    boton_dialogo(sesion, esperar, "Eliminar").click()
    esperar.until(EC.invisibility_of_element_located(fila(nombre_unico)))
    assert not sesion.find_elements(*fila(nombre_unico))


def test_sel06_repuesto_original_se_muestra_como_original(sesion, esperar, nombre_unico):
    """Marcar 'Repuesto original' se refleja en la columna Tipo."""
    try:
        crear_repuesto(sesion, esperar, nombre_unico, parte="QA-006", original=True)
        assert "Original" in sesion.find_element(*fila(nombre_unico)).text
        capturar(sesion, "sel06_repuesto_original")
    finally:
        eliminar_repuesto(sesion, esperar, nombre_unico)
