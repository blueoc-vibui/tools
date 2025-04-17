import os
import re
import time
import random
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
import concurrent.futures

# 📁 Cấu hình profile thật của bạn ở đây
CHROME_USER_DATA_DIR = "/Users/buichivi/Library/Application Support/Google/Chrome"
CHROME_PROFILE_NAME = "Default"  # hoặc "Profile 1", "Profile 2", v.v.

save_folder = "teeshirt_images"
os.makedirs(save_folder, exist_ok=True)

def clean_filename(filename, max_length=255):
    filename = re.sub(r"[^\w\s.-]", "", filename)
    return filename.strip()[:max_length]

def convert_to_logo_image(url: str) -> str:
    url = url.replace("-front", "-swatch")
    url = url.replace("width=400", "width=1500")
    url = url.replace("width=700", "width=1500")
    return url

def create_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--window-size=1200,800")
    options.add_argument(f"--user-data-dir={CHROME_USER_DATA_DIR}")
    options.add_argument(f"--profile-directory={CHROME_PROFILE_NAME}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    return webdriver.Chrome(options=options)

def scroll_to_bottom(driver, pause_time=2, max_attempts=30):
    last_height = driver.execute_script("return document.body.scrollHeight")
    for i in range(max_attempts):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause_time + random.uniform(0.5, 1.5))
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            print(f"🛑 Dừng lại sau {i+1} lần cuộn.")
            break
        last_height = new_height

def get_all_images(url):
    print(f"\n🔍 Truy cập: {url}")
    driver = create_driver()
    try:
        driver.get(url)
        time.sleep(20)
        scroll_to_bottom(driver)

        images = driver.find_elements(By.CSS_SELECTOR, "img[alt][src*='productImages']")
        print(f"✅ Tìm thấy {len(images)} ảnh")

        data = []
        for img in images:
            src = img.get_attribute("src") or img.get_attribute("data-src")
            alt = img.get_attribute("alt") or "image"
            if src and "-front" in src:
                data.append((alt, convert_to_logo_image(src)))
        return data
    finally:
        driver.quit()

def download_image(idx, img_data):
    try:
        name, url = img_data
        filename = clean_filename(name) + ".jpg"
        path = os.path.join(save_folder, filename)
        res = requests.get(url, stream=True, timeout=30)
        if res.status_code == 200:
            with open(path, "wb") as f:
                for chunk in res.iter_content(1024):
                    f.write(chunk)
            print(f"✅ Ảnh {idx+1}: {filename}")
        else:
            print(f"❌ Ảnh {idx+1} lỗi HTTP {res.status_code}")
    except Exception as e:
        print(f"❌ Lỗi tải ảnh {idx+1}: {e}")

if __name__ == "__main__":
    url = "https://www.teeshirtpalace.com/t-shirts"
    images = get_all_images(url)

    print(f"\n📦 Tổng ảnh cần tải: {len(images)}. Bắt đầu tải...\n")
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(download_image, range(len(images)), images)

    print("\n🎉 Xong! Ảnh đã tải về thư mục teeshirt_images.")
