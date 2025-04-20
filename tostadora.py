import os
import pickle
import re
import time
import requests
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By

BASE_URL = "https://www.tostadora.com"
CATEGORY_BASE = "https://www.tostadora.com/t+shirts/?pag={}"
DOWNLOAD_DIR = "tostadora"


def ensure_download_dir():
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)


def convert_image_url(url):
    if not url:
        return None
    url = re.sub(r";w:\d+", ";w:1000", url)
    url = re.sub(r";m:\d+", ";m:0", url)
    return url


def download_image(img_url, filename):
    try:
        resp = requests.get(img_url)
        with open(os.path.join(DOWNLOAD_DIR, filename), "wb") as f:
            f.write(resp.content)
        print(f"✅ Downloaded: {filename}")
    except Exception as e:
        print(f"❌ Failed to download image: {e}")


def crawl_with_stealth_driver(start_page, end_page):
    ensure_download_dir()

    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    # Uncomment to see browser window:
    # options.headless = False

    driver = uc.Chrome(options=options)

    for page_num in range(start_page, end_page + 1):
        url = CATEGORY_BASE.format(page_num)
        print(f"\n🔎 Visiting page {page_num}: {url}")
        driver.get(url)
        time.sleep(10)

        product_cards = driver.find_elements(By.CSS_SELECTOR, ".m-product-card > .m-product-card__img")
        print(f"🔗 Found {len(product_cards)} product cards.")

        product_links = []
        for card in product_cards:
            try:
                href = card.get_attribute("href")
                if href and "/web/" in href:
                    product_links.append(href)
            except:
                continue

        print(f"📦 Collected {len(product_links)} product links.")

        for link in product_links:
            print(f"🧩 Visiting: {link}")
            try:
                driver.get(link)
                time.sleep(8)

                img_list = driver.find_elements(By.CSS_SELECTOR, "#js-slider-container .c-pdp-slider__thumbnail img")
                if len(img_list) >= 1:
                    logo_img = img_list[0]
                    title = driver.find_element(By.CSS_SELECTOR, '.txt-compo-crop')
                    img_url = logo_img.get_attribute("src")
                    fixed_url = convert_image_url(img_url)
                    if fixed_url:
                        filename = title.text + ".jpg"
                        download_image(fixed_url, filename)
                    else:
                        print("⚠️ URL empty after conversion.")
                else:
                    print("⚠️ Not enough images in thumbnail.")
            except Exception as e:
                print(f"❌ Error loading product page: {e}")

    driver.quit()


if __name__ == "__main__":
    try:
        start_page = int(input("🔢 Enter start page: "))
        end_page = int(input("🔢 Enter end page: "))
        crawl_with_stealth_driver(start_page, end_page)
    except ValueError:
        print("❌ Please enter valid page numbers.")
