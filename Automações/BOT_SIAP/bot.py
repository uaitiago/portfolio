# -*- coding: utf-8 -*-

import os
import time
import sys
import traceback
import random

# ====== Selenium / WebDriver ======
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
)

# .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ------------------ CONFIG ------------------
SIAP_URL = "https://siap.educacao.go.gov.br/login.aspx?ReturnUrl=%2fdefault.aspx"
WAIT = 25  # segundos de espera padrão
CLICK_DDL_EIXO = os.getenv("CLICK_DDL_EIXO", "false").lower() in {"1", "true", "yes", "y"}

SIAP_LOGIN = os.getenv("SIAP_LOGIN", "").strip()
SIAP_SENHA = os.getenv("SIAP_SENHA", "").strip()

if not SIAP_LOGIN or not SIAP_SENHA:
    print("ATENÇÃO: Defina SIAP_LOGIN e SIAP_SENHA no .env.")

# ------------------ DRIVER ------------------
def get_auto_chromedriver(options: Options) -> webdriver.Chrome:
    last_error = None
    try:
        service = Service()
        driver = webdriver.Chrome(service=service, options=options)
        print("[OK] Chrome via Selenium Manager.")
        return driver
    except Exception as e:
        last_error = e
        print("[Aviso] Selenium Manager falhou; tentando chromedriver-autoinstaller…")
    try:
        import chromedriver_autoinstaller as cda
        cda.install()
        service = Service()
        driver = webdriver.Chrome(service=service, options=options)
        print("[OK] Chrome via chromedriver-autoinstaller.")
        return driver
    except Exception as e:
        last_error = e
        print("[Aviso] chromedriver-autoinstaller falhou; tentando webdriver-manager…")
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        print("[OK] Chrome via webdriver-manager.")
        return driver
    except Exception as e:
        last_error = e

    print("[ERRO] Não foi possível iniciar o Chrome.")
    traceback.print_exception(type(last_error), last_error, last_error.__traceback__)
    sys.exit(1)

def build_chrome_options(headless: bool = False) -> Options:
    options = Options()
    options.add_argument("--log-level=3")
    options.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    if headless:
        options.add_argument("--headless=new")
    return options

# ------------------ HELPERS GERAIS ------------------
def esperar_elemento(driver, metodo, seletor, tempo=WAIT, clicavel=False):
    cond = EC.element_to_be_clickable if clicavel else EC.presence_of_element_located
    return WebDriverWait(driver, tempo).until(cond((metodo, seletor)))

def esperar_todos_elementos(driver, metodo, seletor, tempo=WAIT):
    return WebDriverWait(driver, tempo).until(EC.presence_of_all_elements_located((metodo, seletor)))

def mover_e_clicar(driver, metodo, seletor, tempo=WAIT):
    elem = esperar_elemento(driver, metodo, seletor, tempo, clicavel=True)
    ActionChains(driver).move_to_element(elem).pause(0.1).click().perform()

def _normalize_txt(s: str) -> str:
    return " ".join(s.split()).strip().lower()

def _scroll_into_view(driver, el):
    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    except Exception:
        pass

def _click_any(driver, el) -> bool:
    """Tenta clicar com várias estratégias."""
    try:
        _scroll_into_view(driver, el)
        driver.execute_script("arguments[0].click();", el)
        return True
    except Exception:
        pass
    try:
        _scroll_into_view(driver, el)
        ActionChains(driver).move_to_element(el).pause(0.05).click().perform()
        return True
    except Exception:
        return False

def wait_postback_done(driver, timeout=WAIT):
    """
    Aguarda fim de (partial) postback:
    - Se houver PageRequestManager (ASP.NET AJAX), espera isInAsyncPostBack == false
    - Caso contrário, espera document.readyState == 'complete'
    """
    end = time.time() + timeout
    last_state = None
    while time.time() < end:
        try:
            is_async = driver.execute_script(
                "try {return !!(window.Sys && Sys.WebForms && "
                "Sys.WebForms.PageRequestManager && "
                "Sys.WebForms.PageRequestManager.getInstance() && "
                "Sys.WebForms.PageRequestManager.getInstance().get_isInAsyncPostBack());} "
                "catch(e){return false;}"
            )
            if not is_async:
                state = driver.execute_script("return document.readyState")
                if state == "complete":
                    if last_state == "complete":
                        return
                    last_state = "complete"
            else:
                last_state = None
        except Exception:
            pass
        time.sleep(0.1)

def switch_to_frame_containing(driver, locator, timeout=WAIT) -> bool:
    """Procura 'locator' no documento atual; se não achar, testa iframes de 1º nível."""
    driver.switch_to.default_content()
    try:
        WebDriverWait(driver, 1.5).until(EC.presence_of_element_located(locator))
        return True
    except TimeoutException:
        pass
    for i, frame in enumerate(driver.find_elements(By.TAG_NAME, "iframe")):
        try:
            driver.switch_to.default_content()
            driver.switch_to.frame(frame)
            WebDriverWait(driver, 1.5).until(EC.presence_of_element_located(locator))
            print(f"[INFO] Alternado p/ iframe #{i} contendo {locator}.")
            return True
        except TimeoutException:
            continue
    driver.switch_to.default_content()
    return False

# ------------------ TREEVIEW ------------------
def get_tree_root(driver):
    tree_locator = (By.ID, "cphFuncionalidade_cphCampos_treeView")
    switch_to_frame_containing(driver, tree_locator, timeout=WAIT)
    raiz = esperar_elemento(driver, *tree_locator, tempo=WAIT)
    return raiz

def get_tree_divs(driver):
    raiz = get_tree_root(driver)
    # DIVs cujos IDs começam com o prefixo e terminam com 'Nodes'
    return raiz.find_elements(
        By.CSS_SELECTOR,
        "div[id^='cphFuncionalidade_cphCampos_treeView'][id$='Nodes']"
    )

def _primeiro_alvo_clicavel_da_table(tb):
    """Dentro da table, tenta um alvo mais 'clicável': checkbox/radio, depois label/a; se nada, a própria table."""
    try:
        alvo = tb.find_element(By.XPATH, ".//input[(@type='checkbox' or @type='radio') and not(@disabled)]")
        return alvo
    except NoSuchElementException:
        pass
    for xp in (".//label", ".//a"):
        try:
            return tb.find_element(By.XPATH, xp)
        except NoSuchElementException:
            continue
    return tb

def click_with_retry(driver, element_getter, after_click_wait=True, max_retries=3):
    """
    element_getter(): função que retorna SEMPRE um elemento FRESCO (rebuscando no DOM).
    Tenta clicar; se houver STALE, re-tenta.
    """
    for attempt in range(1, max_retries + 1):
        try:
            el = element_getter()
            if not el:
                return False
            if _click_any(driver, el):
                if after_click_wait:
                    wait_postback_done(driver, timeout=WAIT)
                return True
        except StaleElementReferenceException:
            if attempt == max_retries:
                raise
            time.sleep(0.2)
            continue
    return False

def _make_div_table_getter(driver, div_index, table_index):
    """
    Retorna uma função que, quando chamada, re-busca a DIV comum `div_index`,
    pega a table `table_index` (com clamp), e devolve um alvo clicável fresco.
    """
    def getter():
        divs2 = get_tree_divs(driver)
        if len(divs2) < 2:
            return None
        comuns2 = divs2[:-2]
        if div_index >= len(comuns2):
            return None
        d = comuns2[div_index]
        tables = d.find_elements(By.TAG_NAME, "table")
        if not tables:
            return None
        idx = min(table_index, len(tables) - 1)
        return _primeiro_alvo_clicavel_da_table(tables[idx])
    return getter

def clicar_ate_3_por_div_comum(driver, n_por_div=3):
    """
    Para cada DIV comum (todas menos as 2 últimas), clica até `n_por_div`
    tables aleatórias. Usa re-busca e retry para evitar elementos stale.
    """
    total = 0
    divs = get_tree_divs(driver)
    if len(divs) < 2:
        return 0
    num_comuns = len(divs) - 2

    for div_index in range(num_comuns):
        clicados_div = 0
        usados = set()
        tentativas = 0

        while clicados_div < n_por_div and tentativas < n_por_div * 6:
            tentativas += 1

            divs2 = get_tree_divs(driver)
            if len(divs2) < 2:
                break
            comuns2 = divs2[:-2]
            if div_index >= len(comuns2):
                break
            d = comuns2[div_index]
            tables = d.find_elements(By.TAG_NAME, "table")
            if not tables:
                break

            disponiveis = [i for i in range(len(tables)) if i not in usados]
            if not disponiveis:
                break

            tb_idx = random.choice(disponiveis)
            getter = _make_div_table_getter(driver, div_index, tb_idx)

            ok = click_with_retry(driver, getter, after_click_wait=True, max_retries=4)
            if ok:
                usados.add(tb_idx)
                clicados_div += 1
                total += 1

        print(f"[treeView] Seção comum #{div_index+1}: {clicados_div} cliques.")

    return total

def clicar_por_texto_em_div(driver, div_index_from_end, textos):
    """
    div_index_from_end: -1 (última) ou -2 (penúltima)
    textos: lista de strings a procurar (case-insensitive, contém). Tenta clicar cada uma.
    """
    total = 0
    for alvo_text in textos:
        alvo_norm = _normalize_txt(alvo_text)

        def getter():
            divs = get_tree_divs(driver)
            if not divs:
                return None
            try:
                div = divs[div_index_from_end]
            except IndexError:
                return None
            for tb in div.find_elements(By.TAG_NAME, "table"):
                if alvo_norm in _normalize_txt(tb.text):
                    return _primeiro_alvo_clicavel_da_table(tb)
            return None

        ok = click_with_retry(driver, getter, after_click_wait=True, max_retries=4)
        if ok:
            total += 1
    return total

def clicar_tables_personalizado(driver):
    """
    - 3 aleatórios **por cada** div comum
    - textos específicos na penúltima e última
    """
    # 1) 3 aleatórios POR DIV COMUM
    total_aleatorios = clicar_ate_3_por_div_comum(driver, n_por_div=3)
    print(f"[treeView] Aleatórios (todas as comuns): {total_aleatorios} cliques.")

    # 2) penúltima (por texto)
    n2 = clicar_por_texto_em_div(
        driver,
        -2,
        [
            "Aula expositiva e produção de texto individual sobre o conteúdo proposto",
            "Resolução de situações-problemas de temática trabalhada",
        ],
    )
    print(f"[treeView] Penúltima: {n2} cliques por texto.")

    # 3) última (por texto)
    n3 = clicar_por_texto_em_div(
        driver,
        -1,
        ["Resolução escrita da atividade individualmente e por alguns alunos no quadro"],
    )
    print(f"[treeView] Última: {n3} cliques por texto.")

# ------------------ LISTAGEM / NAVEGAÇÃO ENTRE TURMAS ------------------
def get_turma_rows(driver):
    """Rebusca e retorna as linhas de turmas da tela de listagem."""
    driver.switch_to.default_content()
    # garante que a listagem está visível (se tiver botão Listar, pode clicar)
    try:
        listar = driver.find_elements(By.ID, "cphFuncionalidade_btnListar")
        if listar:
            _click_any(driver, listar[0])
            wait_postback_done(driver)
    except Exception:
        pass

    rows = esperar_todos_elementos(driver, By.XPATH, "//tr[contains(@onclick, 'Select')]")
    return rows

def click_retomar_and_wait_list(driver):
    """Clica no botão Retornar e espera voltar à listagem de turmas."""
    driver.switch_to.default_content()

    # 1) ID exato do seu HTML
    try:
        btn = esperar_elemento(driver, By.ID, "cphFuncionalidade_btnCancelar", tempo=8, clicavel=True)
        _click_any(driver, btn)
        wait_postback_done(driver)
        get_turma_rows(driver)
        return True
    except Exception:
        pass

    # 2) NAME exato (fallback)
    try:
        btns = driver.find_elements(By.NAME, "ctl00$ctl00$cphFuncionalidade$btnCancelar")
        if btns:
            _click_any(driver, btns[0])
            wait_postback_done(driver)
            get_turma_rows(driver)
            return True
    except Exception:
        pass

    # 3) Fallbacks por texto/valor
    try:
        cand = driver.find_elements(
            By.XPATH,
            "//input[@type='submit' and @value='Retornar'] | //button[normalize-space()='Retornar'] | //a[normalize-space()='Retornar']"
        )
        if cand:
            _click_any(driver, cand[0])
            wait_postback_done(driver)
            get_turma_rows(driver)
            return True
    except Exception:
        pass

    # 4) Último recurso: clicar em 'Listar' para reabrir a lista
    try:
        listar = esperar_elemento(driver, By.ID, "cphFuncionalidade_btnListar", tempo=8, clicavel=True)
        _click_any(driver, listar)
        wait_postback_done(driver)
        get_turma_rows(driver)
        return True
    except Exception:
        print("[INFO] Não consegui acionar 'Retornar' nem 'Listar'.")
        return False

def planear_turma_por_indice(driver, turma_index):
    """
    Entra na turma de índice `turma_index`, clica Editar, planeja aulas, salva,
    e por fim clica Retornar para voltar à listagem.
    Retorna True se finalizou e voltou à lista, False se algo impediu.
    """
    rows = get_turma_rows(driver)
    if turma_index >= len(rows):
        print(f"[AVISO] Índice {turma_index+1} fora do alcance. Total de turmas: {len(rows)}.")
        return False

    # abre turma
    print(f"\n=== Turma #{turma_index+1} de {len(rows)} ===")
    _click_any(driver, rows[turma_index])
    time.sleep(0.7)

    # entra em Editar
    try:
        editar = esperar_elemento(driver, By.ID, "cphFuncionalidade_btnEditar", tempo=WAIT, clicavel=True)
        _click_any(driver, editar)
        wait_postback_done(driver)
    except Exception:
        print("[ERRO] Não foi possível entrar no modo 'Editar' da turma.")
        return False

    # loop de aulas não planejadas
    while True:
        try:
            aulas = esperar_todos_elementos(
                driver,
                By.XPATH,
                "//div[@class='sequencial']//div[contains(@class, 'naoPlanejada')]",
                tempo=8,
            )
        except Exception:
            aulas = []

        if not aulas:
            print("Não há mais aulas não planejadas nesta turma.")
            break

        aula = aulas[0]
        try:
            numero = aula.get_attribute("numeroaula")
        except Exception:
            numero = "?"
        print(f"Processando aula {numero}…")
        driver.execute_script("arguments[0].click();", aula)
        time.sleep(0.3)

        # opcional: ddlEixo
        if CLICK_DDL_EIXO:
            try:
                ddl = esperar_elemento(driver, By.ID, "cphFuncionalidade_cphCampos_ddlEixo", clicavel=True)
                _click_any(driver, ddl)
                wait_postback_done(driver)
            except Exception:
                pass

        # seleção dentro do treeView
        clicar_tables_personalizado(driver)

        # Salvar
        botao = esperar_elemento(driver, By.ID, "cphFuncionalidade_btnAlterar", clicavel=True)
        _click_any(driver, botao)
        wait_postback_done(driver)
        print("✅ Aula salva.")
        time.sleep(0.4)

    # Retornar (voltar à lista)
    ok = click_retomar_and_wait_list(driver)
    if not ok:
        print("[AVISO] Não consegui voltar à listagem automaticamente; tentando 'Listar' novamente.")
        try:
            listar = esperar_elemento(driver, By.ID, "cphFuncionalidade_btnListar", tempo=8, clicavel=True)
            _click_any(driver, listar)
            wait_postback_done(driver)
            get_turma_rows(driver)
            ok = True
        except Exception:
            ok = False

    return ok

# ------------------ FLUXO PRINCIPAL ------------------
def main():
    options = build_chrome_options(headless=False)
    driver = get_auto_chromedriver(options)
    try:
        # Acessa o SIAP
        driver.get(SIAP_URL)
        print("Site aberto com sucesso!")

        # Login
        esperar_elemento(driver, By.ID, "txtLogin").clear()
        esperar_elemento(driver, By.ID, "txtLogin").send_keys(SIAP_LOGIN)
        esperar_elemento(driver, By.ID, "txtSenha").clear()
        esperar_elemento(driver, By.ID, "txtSenha").send_keys(SIAP_SENHA)

        # Captcha (texto simples)
        captcha = esperar_elemento(driver, By.ID, "lblCaptcha").text
        print("Captcha:", captcha)
        esperar_elemento(driver, By.ID, "txtCaptcha").clear()
        esperar_elemento(driver, By.ID, "txtCaptcha").send_keys(captcha)

        time.sleep(0.7)
        esperar_elemento(driver, By.ID, "btnLogon", clicavel=True).click()

        # Menu
        mover_e_clicar(driver, By.CLASS_NAME, "menu_trigger")

        print("\n1 - Planejar Aula\n2 - Executar Aula")
        escolha = input("Digite o número da opção desejada: ").strip()

        if escolha == "1":
            # Planejamento
            mover_e_clicar(driver, By.XPATH, "//a[contains(text(), 'Planejamento')]")
            esperar_elemento(driver, By.TAG_NAME, "body")
            mover_e_clicar(driver, By.ID, "cphFuncionalidade_btnListar")
            wait_postback_done(driver)
            time.sleep(0.8)

            # Mostra lista e pergunta onde começar
            rows = get_turma_rows(driver)
            for idx, tr in enumerate(rows):
                try:
                    tds = tr.find_elements(By.TAG_NAME, "td")
                    texto = " | ".join(td.text for td in tds) if tds else tr.text
                except Exception:
                    texto = tr.text
                print(f"{idx+1} - {texto}")

            try:
                start_idx = int(input("Começar a partir de qual número de turma? ")) - 1
            except ValueError:
                print("Entrada inválida. Abortando.")
                return

            if start_idx < 0 or start_idx >= len(rows):
                print("Índice de turma inválido. Abortando.")
                return

            # Loop pelas turmas: da escolhida até a última
            total_turmas = len(rows)
            for turma_index in range(start_idx, total_turmas):
                ok = planear_turma_por_indice(driver, turma_index)
                if not ok:
                    print(f"[AVISO] Turma #{turma_index+1}: não foi possível completar/retomar. Tentando seguir.")
                    # tenta garantir que estamos na listagem antes de seguir
                    try:
                        get_turma_rows(driver)
                    except Exception:
                        pass

            print("🎉 Todas as turmas (a partir da selecionada) foram processadas.")

        elif escolha == "2":
            mover_e_clicar(driver, By.XPATH, "//a[contains(text(), 'Diário do Professor')]")
            print("Abrindo Diário do Professor…")

        print("Fluxo finalizado.")

    except Exception as e:
        print("Erro:", e)
        traceback.print_exc()
    finally:
        try:
            input("Enter para sair…")
        except Exception:
            pass
        driver.quit()
        print("Navegador fechado!")

if __name__ == "__main__":
    main()
