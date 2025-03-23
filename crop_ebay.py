from PIL import Image
import os

def crop_image(input_path, output_path):
    """
    Cắt ảnh theo vùng cố định dựa trên tỷ lệ từ ảnh mẫu bạn vẽ.
    """
    try:
        image = Image.open(input_path)
        w, h = image.size

        # Crop theo vùng bạn vẽ (tỷ lệ ảnh)
        x1 = int(w * 0.25)
        x2 = int(w * 0.75)
        y1 = int(h * 0.14)
        y2 = int(h * 0.83)

        cropped = image.crop((x1, y1, x2, y2))
        cropped.save(output_path)
        print(f"✅ Đã lưu ảnh cắt tại: {output_path}")
    except Exception as e:
        print(f"❌ Lỗi khi cắt ảnh {input_path}: {e}")

if __name__ == "__main__":
    input_folder = r"/Users/buichivi/Workspaces/tools/ebay"
    output_folder = r"/Users/buichivi/Workspaces/tools/ebay_output"

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    for file_name in os.listdir(input_folder):
        if file_name.lower().endswith((".jpg", ".jpeg", ".png")):
            input_path = os.path.join(input_folder, file_name)
            output_path = os.path.join(output_folder, file_name)
            crop_image(input_path, output_path)
