"""
Quick test: capture screenshot + inspect DOM for 'keyboard' instruction overlays.
"""
import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

SCREENSHOT_PATH = "tmp/dashboard_screenshot.png"
URL = "http://localhost:8501"

def main():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1920,1200")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    
    driver = webdriver.Chrome(options=opts)
    driver.get(URL)
    
    # Wait for Streamlit to finish loading
    print("[*] Waiting for Streamlit app to load...")
    try:
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="stAppViewContainer"]'))
        )
        time.sleep(5)  # Extra wait for full render
    except Exception as e:
        print(f"[!] Timeout waiting for app: {e}")
    
    # Take full page screenshot
    driver.save_screenshot(SCREENSHOT_PATH)
    print(f"[+] Screenshot saved to {SCREENSHOT_PATH}")
    
    # Find ALL elements containing 'keyboard' text
    print("\n[*] Searching for elements containing 'keyboard' text...")
    keyboard_elements = driver.execute_script("""
        var results = [];
        document.querySelectorAll('*').forEach(function(el) {
            // Check direct text content (not children's text)
            var directText = '';
            for (var i = 0; i < el.childNodes.length; i++) {
                if (el.childNodes[i].nodeType === 3) {
                    directText += el.childNodes[i].textContent;
                }
            }
            var fullText = (el.textContent || '').trim();
            if (fullText.toLowerCase().includes('keyboard') || 
                fullText.toLowerCase().includes('double_arrow')) {
                var info = {
                    tag: el.tagName,
                    id: el.id || '',
                    className: el.className || '',
                    dataTestId: el.getAttribute('data-testid') || '',
                    directText: directText.trim().substring(0, 100),
                    fullText: fullText.substring(0, 100),
                    parentTag: el.parentElement ? el.parentElement.tagName : '',
                    parentClass: el.parentElement ? (el.parentElement.className || '').substring(0, 100) : '',
                    parentDataTestId: el.parentElement ? (el.parentElement.getAttribute('data-testid') || '') : '',
                    grandparentClass: (el.parentElement && el.parentElement.parentElement) ? 
                        (el.parentElement.parentElement.className || '').substring(0, 100) : '',
                    grandparentDataTestId: (el.parentElement && el.parentElement.parentElement) ? 
                        (el.parentElement.parentElement.getAttribute('data-testid') || '') : '',
                    isVisible: el.offsetParent !== null,
                    display: window.getComputedStyle(el).display,
                    visibility: window.getComputedStyle(el).visibility,
                    height: el.offsetHeight,
                    width: el.offsetWidth,
                    childCount: el.children.length,
                    cssSelector: (function() {
                        try {
                            if (el.id) return '#' + el.id;
                            var path = [];
                            var current = el;
                            while (current && current !== document.body) {
                                var sel = current.tagName.toLowerCase();
                                if (current.getAttribute('data-testid')) {
                                    sel = '[data-testid="' + current.getAttribute('data-testid') + '"]';
                                    path.unshift(sel);
                                    break;
                                }
                                path.unshift(sel);
                                current = current.parentElement;
                            }
                            return path.join(' > ');
                        } catch(e) { return ''; }
                    })()
                };
                results.push(info);
            }
        });
        return results;
    """)
    
    if keyboard_elements:
        print(f"\n[+] Found {len(keyboard_elements)} elements containing 'keyboard'/'double_arrow':\n")
        for i, el in enumerate(keyboard_elements):
            print(f"--- Element {i+1} ---")
            print(f"  Tag: {el['tag']}")
            print(f"  Class: {el['className'][:120]}")
            print(f"  data-testid: {el['dataTestId']}")
            print(f"  Direct text: {repr(el['directText'])}")
            print(f"  Full text: {repr(el['fullText'][:80])}")
            print(f"  Visible: {el['isVisible']}, display: {el['display']}, visibility: {el['visibility']}")
            print(f"  Size: {el['width']}x{el['height']}")
            print(f"  Children: {el['childCount']}")
            print(f"  Parent: {el['parentTag']} class={el['parentClass'][:80]}")
            print(f"  Parent data-testid: {el['parentDataTestId']}")
            print(f"  Grandparent class: {el['grandparentClass'][:80]}")
            print(f"  Grandparent data-testid: {el['grandparentDataTestId']}")
            print(f"  CSS selector: {el['cssSelector']}")
            print()
    else:
        print("[+] No elements found with 'keyboard' or 'double_arrow' text")
    
    driver.quit()
    print("[*] Done")

if __name__ == "__main__":
    main()
