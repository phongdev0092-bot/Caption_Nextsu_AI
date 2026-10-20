# -*- coding: utf-8 -*-
import sys, time, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r"d:\Data Retrieval Tool")

from selenium.webdriver.common.by import By
import core_login

driver = core_login.create_driver_with_retry(headless=True)
try:
    url = "http://login.fpt.net/?urlreturn=inside.fpt.net"
    print(f"Navigating to {url}...")
    driver.get(url)
    time.sleep(3)
    print("Current URL:", driver.current_url)
    print("Title:", driver.title)
    inputs = driver.find_elements(By.TAG_NAME, "input")
    print(f"Inputs count: {len(inputs)}")
    for i, inp in enumerate(inputs):
        print(f"  [{i}] id={inp.get_attribute('id')!r}, name={inp.get_attribute('name')!r}, type={inp.get_attribute('type')!r}")
    
    # Also check inside.fpt.net/default.asp
    print("\nNavigating to http://inside.fpt.net/default.asp...")
    driver.get("http://inside.fpt.net/default.asp")
    time.sleep(3)
    print("default.asp URL:", driver.current_url)
    print("default.asp Title:", driver.title)
    frames = driver.find_elements(By.TAG_NAME, "iframe")
    print(f"Iframes in default.asp: {len(frames)}")
    for f in range(len(frames)):
        driver.switch_to.default_content()
        driver.switch_to.frame(f)
        finps = driver.find_elements(By.TAG_NAME, "input")
        print(f"  Frame [{f}] inputs: {len(finps)}")
        for i, fi in enumerate(finps[:5]):
            print(f"    [{i}] id={fi.get_attribute('id')!r}, name={fi.get_attribute('name')!r}")
finally:
    driver.quit()
