import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import threading

# ========== Cấu hình ==========

HEADLESS = True            # True = chạy ẩn Chrome, False = hiện Chrome để debug
START_PAGE = 1             # Trang bắt đầu
END_PAGE = 5               # Trang kết thúc
MAX_WORKERS = 10           # Số luồng tải ảnh song song
PAUSE_AFTER_IMAGES = 10     # Sau bao nhiêu ảnh thì nghỉ
PAUSE_SECONDS = 5          # Nghỉ bao nhiêu giây
SAVE_FOLDER = 'teezily'

# ========== Khởi tạo Selenium Driver ==========

options = webdriver.ChromeOptions()
options.add_argument('--start-maximized')
if HEADLESS:
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

driver = webdriver.Chrome(options=options)

# ========== Các hàm xử lý ==========

image_links = []

def collect_images():
    """Thu thập link ảnh và alt text"""
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    img_tags = soup.select('img.img-fluid')
    for img in img_tags:
        img_url = img.get('src')
        alt_text = img.get('alt', 'no_alt').replace('/', '_').replace('\\', '_')
        if img_url:
            # Sửa link thành size 2000x2000
            new_url = img_url.replace('/195/195/', '/2000/2000/')
            image_links.append((new_url, alt_text))

def go_to_page(page_number):
    """Chuyển trang"""
    pagination_items = driver.find_elements(By.CSS_SELECTOR, '.pagination .page-item')
    for item in pagination_items:
        try:
            button = item.find_element(By.CSS_SELECTOR, 'button.page-link')
            if button.text.strip() == str(page_number):
                ActionChains(driver).move_to_element(button).click(button).perform()
                print(f"Moved to page {page_number}")
                return True
        except:
            continue
    print(f"Page {page_number} not found.")
    return False

# Thread-safe counter để pause
download_counter = 0
download_lock = threading.Lock()

def download_image(data):
    """Tải ảnh về"""
    global download_counter
    img_url, alt_text = data
    filename = alt_text + '.jpg'
    filepath = os.path.join(SAVE_FOLDER, filename)
    try:
        response = requests.get(img_url, timeout=15)
        if response.status_code == 200:
            with open(filepath, 'wb') as f:
                f.write(response.content)
            print(f"Downloaded: {filename}")
        else:
            print(f"Failed (Status {response.status_code}): {filename}")
    except Exception as e:
        print(f"Failed: {filename} with error {e}")

    with download_lock:
        download_counter += 1
        if download_counter % PAUSE_AFTER_IMAGES == 0:
            print(f"Downloaded {download_counter} images, pausing {PAUSE_SECONDS}s to avoid server blocking...")
            time.sleep(PAUSE_SECONDS)

# ========== Chạy chính ==========

def main():
    # Tạo folder lưu ảnh
    os.makedirs(SAVE_FOLDER, exist_ok=True)

    # Mở web
    url = 'https://www.teezily.com/en/shop/t-shirts'
    driver.get(url)
    time.sleep(10)

    # Click switch button
    try:
        switch_buttons = driver.find_element(By.CSS_SELECTOR, '.col-6.mb-3.switch-design.text-end')
        buttons = switch_buttons.find_elements(By.TAG_NAME, 'button')
        buttons[1].click()
        print("Clicked switch button successfully.")
    except Exception as e:
        print("Error clicking switch button:", e)
    time.sleep(10)

    # Thu thập ảnh từ các trang
    for page in range(START_PAGE, END_PAGE + 1):
        if page == START_PAGE:
            collect_images()
        else:
            if go_to_page(page):
                time.sleep(10)
                collect_images()

    driver.quit()

    # Multi-thread download
    print(f"Start downloading {len(image_links)} images with {MAX_WORKERS} threads...")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        executor.map(download_image, image_links)

    print("All downloads finished!")

# ========== Start ==========

if __name__ == '__main__':
    main()
