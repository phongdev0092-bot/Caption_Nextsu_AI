# -*- coding: utf-8 -*-
"""Debug: dump all inputs + buttons in Frame 1 of Thong tin chung page."""
import sys, time, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r"d:\Data Retrieval Tool")

from selenium.webdriver.common.by import By
from inside_cls import InsideClearClsAutomation

print("=== DEBUG: Navigate to Thong tin chung ===")
bot = InsideClearClsAutomation(headless=False, keep_open=True)
bot.init_driver()
driver = bot.driver

try:
    bot.navigate_to_general_info_page()
    print("[OK] Frame 1 loaded")
    time.sleep(2)

    # ---- Helper: dump frame context ----
    def dump_frame(label):
        print(f"\n--- {label} ---")
        # All inputs
        inputs = driver.find_elements(By.TAG_NAME, "input")
        print(f"  inputs: {len(inputs)}")
        for idx, el in enumerate(inputs):
            try:
                typ  = el.get_attribute("type") or ""
                name = el.get_attribute("name") or ""
                eid  = el.get_attribute("id") or ""
                ph   = el.get_attribute("placeholder") or ""
                cls  = el.get_attribute("class") or ""
                vis  = el.is_displayed()
                print(f"    [{idx}] type={typ!r} name={name!r} id={eid!r} ph={ph!r} cls={cls!r} vis={vis}")
            except Exception as ex:
                print(f"    [{idx}] ERR: {ex}")

        # Buttons / anchors with 'Phieu' or 'PTC'
        btns = driver.find_elements(By.XPATH,
            "//*[self::button or self::a or self::input[@type='button'] or self::input[@type='submit']]"
        )
        phieu_btns = []
        for b in btns:
            try:
                txt = (b.text or "").strip()
                val = b.get_attribute("value") or ""
                onc = b.get_attribute("onclick") or ""
                if "phi" in txt.lower() or "phi" in val.lower() or "PTC" in onc or "ptc" in onc.lower():
                    phieu_btns.append(b)
            except Exception:
                pass
        print(f"  ptc-related btns: {len(phieu_btns)}")
        for idx, b in enumerate(phieu_btns):
            try:
                print(f"    [{idx}] tag={b.tag_name} text={b.text[:40]!r} "
                      f"id={b.get_attribute('id')!r} onclick={str(b.get_attribute('onclick'))[:80]!r}")
            except Exception as ex:
                print(f"    [{idx}] ERR: {ex}")

    # ---- Scan Frame 1 (current context) ----
    dump_frame("FRAME 1 (direct)")

    # ---- Scan child iframes inside Frame 1 ----
    child_iframes = driver.find_elements(By.TAG_NAME, "iframe")
    print(f"\nChild iframes in Frame1: {len(child_iframes)}")
    for ci, _ in enumerate(child_iframes):
        try:
            driver.switch_to.frame(ci)
            dump_frame(f"CHILD-IFRAME[{ci}]")
            # 1 level deeper
            grand = driver.find_elements(By.TAG_NAME, "iframe")
            for gi, _ in enumerate(grand):
                try:
                    driver.switch_to.frame(gi)
                    dump_frame(f"CHILD-IFRAME[{ci}] > GRAND[{gi}]")
                    driver.switch_to.parent_frame()
                except Exception:
                    driver.switch_to.parent_frame()
            driver.switch_to.parent_frame()
        except Exception as ex:
            print(f"  iframe[{ci}] ERR: {ex}")
            try:
                driver.switch_to.default_content()
                driver.switch_to.frame(1)
            except Exception:
                pass

    print("\n=== DONE. Chrome stays open. Close manually. ===")

except Exception as e:
    import traceback
    print(f"[ERROR] {e}")
    traceback.print_exc()
