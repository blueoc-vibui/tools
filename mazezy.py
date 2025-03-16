import os
import time
import requests
import concurrent.futures
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

# Cấu hình Selenium
chrome_options = Options()
chrome_options.add_argument("--headless")  # Chạy không mở trình duyệt
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920x1080")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

# Nhập thông tin từ người dùng
base_url = "https://mazezy.com"
path = input("Nhập path: ").strip()
start_page = int(input("Nhập trang bắt đầu: "))
end_page = int(input("Nhập trang kết thúc: "))

# Tạo thư mục lưu ảnh
save_folder = "mazezy"
os.makedirs(save_folder, exist_ok=True)

def clean_filename(filename, max_length=255):
    """Làm sạch tên file để tránh lỗi khi lưu."""
    filename = re.sub(r'[^\w\s.-]', '', filename)  # Chỉ giữ chữ, số, `_`, `-`, `.`
    return filename.strip()[:max_length]  # Giới hạn độ dài file

def get_image_links(page):
    """Lấy danh sách ảnh từ trang bằng Selenium."""
    url = f"{base_url}{path}{'&' if '?' in path else '?'}page={page}"
    print(f"🔍 Đang tải trang: {url}")
    
    driver.get(url)
    time.sleep(5)  # Chờ JavaScript tải ảnh

    # Lấy danh sách ảnh từ class phù hợp
    img_elements = driver.find_elements(By.CSS_SELECTOR, "article img.aspect-square.w-full.object-cover.shadow.rounded-lg")

    image_data = []
    for img in img_elements:
        img_url = img.get_attribute("src").replace("336x336", "3000x3000")  # Lấy ảnh chất lượng cao
        img_name = img.get_attribute("alt")
        
        if img_url and img_name:
            image_data.append((img_name, img_url))  # Lưu dưới dạng (tên, url)

    print(f"✅ Tìm thấy {len(image_data)} ảnh trên trang {page}")
    return image_data

def download_image(idx, img_data):
    """Tải ảnh từ URL và lưu với tên file hợp lệ."""
    try:
        img_name, img_url = img_data
        img_name = clean_filename(img_name)  # Làm sạch tên file
        img_path = os.path.join(save_folder, f"{img_name}.jpg")

        response = requests.get(img_url, stream=True, timeout=10)
        if response.status_code == 200:
            with open(img_path, "wb") as file:
                for chunk in response.iter_content(1024):
                    file.write(chunk)
            print(f"✅ Ảnh {idx+1} tải về: {img_name}")
        else:
            print(f"❌ Lỗi tải ảnh {idx+1}: {img_url}")
    except Exception as e:
        print(f"❌ Lỗi khi tải ảnh {idx+1}: {e}")

# Lấy danh sách ảnh từ nhiều trang
all_images = []
for page in range(start_page, end_page + 1):
    all_images.extend(get_image_links(page))

print(f"📸 Tổng số ảnh tìm thấy: {len(all_images)}. Bắt đầu tải...")

# Dùng đa luồng để tải ảnh nhanh hơn
max_threads = 5
with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
    executor.map(download_image, range(len(all_images)), all_images)

print("✅ Hoàn thành tải ảnh!")

# Đóng trình duyệt
driver.quit()
