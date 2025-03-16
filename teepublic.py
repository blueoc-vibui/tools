import os
import time
import requests
import concurrent.futures
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import random

# Nhập thông tin từ người dùng
base_url = "https://www.teepublic.com"
path = input("Nhập path (ví dụ: /t-shirts): ").strip()
start_page = int(input("Nhập trang bắt đầu: "))
end_page = int(input("Nhập trang kết thúc: "))

# Cấu hình proxy
proxy = {
    "http": "http://root:kPEV5b4r@23.129.232.126:56259",
    "https": "http://root:kPEV5b4r@23.129.232.126:56259"
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
}

# Cấu hình session với Retry
session = requests.Session()
retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
session.mount("https://", HTTPAdapter(max_retries=retries))

# Tạo thư mục lưu ảnh
save_folder = "teepublic"
os.makedirs(save_folder, exist_ok=True)

def get_product_links(page_number):
    """Lấy danh sách href từ một trang cụ thể."""
    url = f"{base_url}{path}{'&' if '?' in path else '?'}page={page}"
    print(url)
    time.sleep(2)  # Chờ để tránh bị chặn
    response = session.get(url, headers=headers, proxies=proxy, timeout=10)
    if response.status_code != 200:
        print(f"Không thể truy cập trang {url}")
        return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    links = soup.select(".tp-design-tile__image-wrap > a:first-child")
    return [link.get("href") for link in links if link.get("href")]

def download_image(idx, href):
    """Tải ảnh từ trang sản phẩm."""
    try:
        time.sleep(2)  # Tránh bị chặn do gửi request quá nhanh
        product_page = session.get(base_url + href, headers=headers, proxies=proxy, timeout=10)
        if product_page.status_code != 200:
            print(f"❌ Không thể truy cập {href}")
            return

        product_soup = BeautifulSoup(product_page.text, "html.parser")
        img_tag = product_soup.select_one("img.jsProductMainImage")

        if img_tag and img_tag.get("src"):
            img_url = img_tag["src"]
            img_name = img_tag["alt"].replace("/", "-")  # Tránh lỗi tên file
            img_path = os.path.join(save_folder, f"{img_name}.jpg")

            # Tải ảnh về qua proxy
            response = session.get(img_url, stream=True, proxies=proxy, timeout=10)
            if response.status_code == 200:
                with open(img_path, "wb") as file:
                    for chunk in response.iter_content(1024):
                        file.write(chunk)
                print(f"✅ Ảnh {idx+1} tải về: {img_name}")
            else:
                print(f"❌ Lỗi tải ảnh {idx+1}: {img_url}")
        else:
            print(f"⚠ Không tìm thấy ảnh chính trên trang {href}")
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