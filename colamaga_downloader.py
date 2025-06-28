#!/usr/bin/env python3
"""
Colamaga Image Downloader
Auto download images from colamaga.com product pages
"""

import os
import re
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urljoin, urlparse
import argparse
from typing import List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock


class ColamagaDownloader:
    def __init__(self, download_folder: str = "downloads", headless: bool = True, max_workers: int = 5, filter_keywords: bool = True):
        """
        Initialize the downloader
        
        Args:
            download_folder: Folder to save downloaded images
            headless: Run browser in headless mode
            max_workers: Maximum number of threads for downloading images
            filter_keywords: Enable keyword filtering from keyTm.txt
        """
        self.download_folder = download_folder
        self.headless = headless
        self.max_workers = max_workers
        self.filter_keywords = filter_keywords
        self.driver = None
        self.print_lock = Lock()  # For thread-safe printing
        self.blocked_keywords = self.load_blocked_keywords() if filter_keywords else []
        self.setup_driver()
        self.setup_download_folder()

    def setup_driver(self):
        """Setup Chrome driver with options"""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-images")  # Don't load images in browser to speed up

        # User agent to avoid detection
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

        try:
            self.driver = webdriver.Chrome(options=chrome_options)
        except Exception as e:
            print(f"Error setting up Chrome driver: {e}")
            print("Please make sure ChromeDriver is installed and in your PATH")
            raise

    def setup_download_folder(self):
        """Create download folder if it doesn't exist"""
        if not os.path.exists(self.download_folder):
            os.makedirs(self.download_folder)
            print(f"Created download folder: {self.download_folder}")

    def sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename for safe saving

        Args:
            filename: Original filename

        Returns:
            Sanitized filename
        """
        # Remove or replace invalid characters - put dash at end to avoid range interpretation
        filename = re.sub(r'[^\w\s.-]', '', filename)
        filename = re.sub(r'[\s-]+', '-', filename)
        return filename.strip('-')

    def safe_print(self, message: str):
        """Thread-safe printing"""
        with self.print_lock:
            print(message)
            
    def download_image(self, img_url: str, img_name: str, page_num: int) -> bool:
        """
        Download a single image
        
        Args:
            img_url: URL of the image
            img_name: Name for the image file
            page_num: Page number for organization
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if image name contains blocked keywords
            if self.is_keyword_blocked(img_name):
                self.safe_print(f"  🚫 Blocked: {img_name} (contains filtered keyword)")
                return False
                
            # Get file extension from URL
            parsed_url = urlparse(img_url)
            ext = os.path.splitext(parsed_url.path)[1] or '.jpg'
            
            # Sanitize filename
            safe_name = self.sanitize_filename(img_name)
            filename = f"{safe_name}{ext}"
            filepath = os.path.join(self.download_folder, filename)

            # Skip if file already exists
            if os.path.exists(filepath):
                self.safe_print(f"  ⏭️  Skipping {filename} (already exists)")
                return True

            # Download the image with faster settings
            response = requests.get(img_url, timeout=15, headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }, stream=True)  # Use streaming for better memory usage
            response.raise_for_status()

            # Save the image
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            self.safe_print(f"  ✅ Downloaded: {filename}")
            return True

        except Exception as e:
            self.safe_print(f"  ❌ Failed to download {img_name}: {e}")
            return False

    def get_page_images(self, page_url: str, page_num: int) -> List[Tuple[str, str]]:
        """
        Extract image URLs and names from a page

        Args:
            page_url: URL of the page to scrape
            page_num: Page number

        Returns:
            List of tuples (img_url, img_name)
        """
        try:
            print(f"\n📄 Processing page {page_num}: {page_url}")
            self.driver.get(page_url)

            # Wait for products to load
            WebDriverWait(self.driver, 5).until(  # Reduced wait time
                EC.presence_of_element_located((By.CSS_SELECTOR, ".product-small.box"))
            )

            # Reduced wait time for images to load
            time.sleep(1)

            # Get product boxes
            product_boxes = self.driver.find_elements(By.CSS_SELECTOR, ".product-small.box")
            print(f"  Found {len(product_boxes)} products")

            images_data = []

            for i, box in enumerate(product_boxes):
                try:
                    # Get image element
                    img_element = box.find_element(By.CSS_SELECTOR, ".box-image img")
                    img_url = img_element.get_attribute("src") or img_element.get_attribute("data-src")

                    # Get product name
                    name_element = box.find_element(By.CSS_SELECTOR, ".name.product-title a")
                    img_name = name_element.text.strip()

                    if img_url and img_name:
                        # Handle relative URLs
                        if img_url.startswith('//'):
                            img_url = 'https:' + img_url
                        elif img_url.startswith('/'):
                            img_url = urljoin(page_url, img_url)

                        # Check if image name contains blocked keywords
                        if self.is_keyword_blocked(img_name):
                            self.safe_print(f"  🚫 Skipping {img_name} (blocked keyword)")
                            continue

                        images_data.append((img_url, img_name))
                        print(f"  📸 Found: {img_name}")
                    else:
                        print(f"  ⚠️  Missing data for product {i+1}")

                except Exception as e:
                    print(f"  ⚠️  Error processing product {i+1}: {e}")
                    continue

            return images_data

        except Exception as e:
            print(f"  ❌ Error loading page {page_num}: {e}")
            return []

    def download_pages(self, base_url: str, start_page: int = 1, end_page: int = 10):
        """
        Download images from multiple pages

        Args:
            base_url: Base URL (e.g., https://colamaga.com/product-category/vintage/)
            start_page: Starting page number
            end_page: Ending page number
        """
        print(f"🚀 Starting download from page {start_page} to {end_page}")
        print(f"📁 Download folder: {os.path.abspath(self.download_folder)}")

        total_images = 0
        total_downloaded = 0

        for page_num in range(start_page, end_page + 1):
            try:
                # Construct page URL
                if page_num == 1:
                    page_url = base_url.rstrip('/')
                else:
                    page_url = f"{base_url.rstrip('/')}/page/{page_num}/"

                # Get images from this page
                images_data = self.get_page_images(page_url, page_num)
                total_images += len(images_data)

                if not images_data:
                    print(f"  ⚠️  No images found on page {page_num}, might be end of pages")
                    continue

                # Download each image using multithreading
                print(f"  📥 Downloading {len(images_data)} images from page {page_num} using {self.max_workers} threads...")
                page_downloaded = 0

                # Use ThreadPoolExecutor for parallel downloads
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    # Submit all download tasks
                    future_to_data = {
                        executor.submit(self.download_image, img_url, img_name, page_num): (img_url, img_name)
                        for img_url, img_name in images_data
                    }

                    # Process completed downloads
                    for future in as_completed(future_to_data):
                        if future.result():
                            page_downloaded += 1
                            total_downloaded += 1

                print(f"  ✅ Page {page_num} complete: {page_downloaded}/{len(images_data)} downloaded")

            except Exception as e:
                print(f"  ❌ Error processing page {page_num}: {e}")
                continue

            # Smaller delay between pages
            time.sleep(0.3)

        print(f"\n🎉 Download complete!")
        print(f"📊 Total: {total_downloaded}/{total_images} images downloaded")
        print(f"📁 Saved to: {os.path.abspath(self.download_folder)}")

    def load_blocked_keywords(self) -> List[str]:
        """
        Load blocked keywords from keyTm.txt file
        
        Returns:
            List of keywords to filter out (case insensitive)
        """
        keywords = []
        keyfile_path = os.path.join(os.path.dirname(__file__), "keyTm.txt")
        
        try:
            with open(keyfile_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith('#'):
                        keywords.append(line.lower())
            
            print(f"🚫 Loaded {len(keywords)} blocked keywords from keyTm.txt")
            return keywords
            
        except FileNotFoundError:
            print("⚠️  keyTm.txt not found, keyword filtering disabled")
            return []
        except Exception as e:
            print(f"⚠️  Error loading keyTm.txt: {e}")
            return []

    def is_keyword_blocked(self, text: str) -> bool:
        """
        Check if text contains any blocked keywords
        
        Args:
            text: Text to check
            
        Returns:
            True if text contains blocked keywords, False otherwise
        """
        if not self.filter_keywords or not self.blocked_keywords:
            return False
            
        text_lower = text.lower()
        
        for keyword in self.blocked_keywords:
            if keyword in text_lower:
                return True
                
        return False

    def close(self):
        """Close the driver"""
        if self.driver:
            self.driver.quit()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def main():
    parser = argparse.ArgumentParser(description="Download images from Colamaga.com")
    parser.add_argument("--url", "-u",
                       default="https://colamaga.com/product-category/vintage/",
                       help="Base URL to download from")
    parser.add_argument("--start", "-s", type=int, default=1,
                       help="Starting page number (default: 1)")
    parser.add_argument("--end", "-e", type=int, default=10,
                       help="Ending page number (default: 10)")
    parser.add_argument("--output", "-o", default="colamaga_images",
                       help="Output folder name (default: colamaga_images)")
    parser.add_argument("--threads", "-t", type=int, default=5,
                       help="Number of download threads (default: 5)")
    parser.add_argument("--no-filter", action="store_true",
                       help="Disable keyword filtering")
    parser.add_argument("--visible", action="store_true",
                       help="Run browser in visible mode (not headless)")

    args = parser.parse_args()

    try:
        with ColamagaDownloader(
            download_folder=args.output,
            headless=not args.visible,
            max_workers=args.threads,
            filter_keywords=not args.no_filter
        ) as downloader:
            downloader.download_pages(args.url, args.start, args.end)

    except KeyboardInterrupt:
        print("\n\n⚠️  Download interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
