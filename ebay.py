import os
import time
import re
import random
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import concurrent.futures
from fake_useragent import UserAgent

# ⚙️ Cấu hình
use_proxy = False
proxy_str = "http://root:16ffdb4b@192.110.164.155:31068"
save_folder = "ebay"
os.makedirs(save_folder, exist_ok=True)

# 🧼 Làm sạch tên ảnh
def clean_filename(filename, max_length=255):
    filename = re.sub(r'[^\w\s.-]', '', filename)
    return filename.strip()[:max_length]

# 🚀 Tạo trình duyệt Chrome
def create_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")  # Bật nếu không cần hiện cửa sổ
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")

    ua = UserAgent()
    chrome_options.add_argument(f"user-agent={ua.random}")

    if use_proxy:
        chrome_options.add_argument(f"--proxy-server={proxy_str}")

    return webdriver.Chrome(options=chrome_options)

# 🖼️ Lấy danh sách ảnh từ 1 trang
def get_image_links(shopname, page):
    base_url = f"https://www.ebay.com/str/{shopname}/?_fcid=1"
    url = f"{base_url}&_pgn={page}&_tab=shop"
    print(f"\n🔍 Truy cập: {url}")

    try:
        driver = create_driver()
        driver.set_page_load_timeout(30)
        driver.get(url)
        time.sleep(random.uniform(3, 5))
        # time.sleep(10)

        images = driver.find_elements(By.CSS_SELECTOR, "article.StoreFrontItemCard img")
        image_names = driver.find_elements(By.CSS_SELECTOR, "article.StoreFrontItemCard h3.str-card-title span.str-text-span")

        data = []

        for img, name_elem in zip(images, image_names):
            img_url = img.get_attribute("src")
            img_name = name_elem.get_attribute("innerText")

            print("img_url: ", img_url)
            print("img_name: ", img_name)

            if img_url and img_name:
                # Tăng chất lượng ảnh (nếu có thể)
                img_url = re.sub(r's-l\d+', 's-l2000', img_url)
                data.append((img_name, img_url))

        print(f"✅ Trang {page}: tìm thấy {len(data)} ảnh")
        return data

    except Exception as e:
        print(f"❌ Lỗi khi truy cập {url}: {e}")
        return []
    finally:
        driver.quit()


# 💾 Tải ảnh
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
            print(f"❌ Ảnh {idx+1} lỗi: HTTP {res.status_code}")
    except Exception as e:
        print(f"❌ Lỗi tải ảnh {idx+1}: {e}")

# 🏁 Chạy chính
if __name__ == "__main__":
    shopname = str(input("Tên shop: "))
    start_page = int(input("Trang bắt đầu: "))
    end_page = int(input("Trang kết thúc: "))

    all_images = []
    for page in range(start_page, end_page + 1):
        images = get_image_links(shopname, page)
        all_images.extend(images)

    print(f"\n📦 Tổng ảnh cần tải: {len(all_images)}. Bắt đầu tải...\n")

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(download_image, range(len(all_images)), all_images)

    print("\n🎉 Xong rồi! Tất cả ảnh đã được tải.")
