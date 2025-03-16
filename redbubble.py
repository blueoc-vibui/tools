import os
import time
import cloudscraper
import concurrent.futures
from bs4 import BeautifulSoup
import random

# Sử dụng cloudscraper để vượt Cloudflare
session = cloudscraper.create_scraper()

# Nhập thông tin từ người dùng
base_url = "https://www.redbubble.com"
path = input("Nhập path (ví dụ: /t-shirts): ").strip()
start_page = int(input("Nhập trang bắt đầu: "))
end_page = int(input("Nhập trang kết thúc: "))

proxy = {
    "http": "http://root:kPEV5b4r@23.129.232.126:56259",
    "https": "http://root:kPEV5b4r@23.129.232.126:56259"
}

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
}

# Tạo thư mục lưu ảnh
save_folder = "redbubble"
os.makedirs(save_folder, exist_ok=True)

import re
def clean_filename(filename, max_length=255):
    """Loại bỏ ký tự đặc biệt, giới hạn độ dài tên file."""
    filename = re.sub(r'[^a-zA-Z0-9 _-]', '', filename)  # Chỉ giữ chữ, số, `_` và `-`
    return filename.strip().replace(' ', '_').replace('_', ' ')[:max_length]

def get_product_links(page_number):
    """Lấy danh sách href từ một trang cụ thể."""
    url = f"{base_url}{path}{'&' if '?' in path else '?'}page={page}"
    time.sleep(4)  # Tránh bị chặn
    response = session.get(url, headers=headers, proxies=proxy, timeout=10)
    if response.status_code != 200:
        print(f"Không thể truy cập trang {url}")
        return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    links = soup.select("a[data-testid='related-work-card']")
    return [link.get("href") for link in links if link.get("href")]

def download_image(idx, href):
    """Tải ảnh từ trang sản phẩm."""
    try:
        time.sleep(random.uniform(2, 5))  # Tránh bị chặn do gửi request quá nhanh
        product_page = session.get(base_url + href, headers=headers, proxies=proxy, timeout=10)
        if product_page.status_code != 200:
            print(f"❌ Không thể truy cập {href}")
            return

        # Lưu Cookie từ trang sản phẩm
        session.cookies.update(product_page.cookies)

        product_soup = BeautifulSoup(product_page.text, "html.parser")
        img_tag = product_soup.select("picture.Picture_picture__Gztgz.Picture_rounded__PvnLg > img")[1]
        
        if not img_tag:
            print(f"⚠ Không tìm thấy ảnh chính trên trang {href}")
            return

        img_url = img_tag["src"]
        img_name = clean_filename(img_tag["alt"])  # Tránh lỗi tên file
        img_path = os.path.join(save_folder, f"{img_name}.jpg")

        # Cập nhật headers với Referer từ trang sản phẩm
        img_headers = headers.copy()
        img_headers["Referer"] = base_url + href  

        # Tải ảnh với Cookie từ session
        response = session.get(img_url, headers=img_headers, proxies=proxy, timeout=10, stream=True)
        if response.status_code == 200:
            with open(img_path, "wb") as file:
                for chunk in response.iter_content(1024):
                    file.write(chunk)
            print(f"✅ Ảnh {idx+1} tải về: {img_name}")
        else:
            print(f"❌ Lỗi tải ảnh {idx+1}: {img_url} (Lỗi {response.status_code})")
    except Exception as e:
        print(f"❌ Lỗi khi xử lý {href}: {e}")

# Lấy danh sách sản phẩm từ nhiều trang
all_hrefs = []
for page in range(start_page, end_page + 1):
    print(f"🔍 Đang lấy danh sách sản phẩm từ trang {page}...")
    all_hrefs.extend(get_product_links(page))

print(f"Tổng số sản phẩm tìm thấy: {len(all_hrefs)}. Bắt đầu tải ảnh...")

# Sử dụng ThreadPoolExecutor để giới hạn số luồng (giảm lỗi kết nối)
max_threads = 5
with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
    executor.map(download_image, range(len(all_hrefs)), all_hrefs)

print("✅ Hoàn thành tải ảnh!")
