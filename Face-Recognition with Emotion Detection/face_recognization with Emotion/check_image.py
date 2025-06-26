import os
import warnings
from PIL import Image
def check_png(filename):
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        try:
            img=Image.open(filename)
            img.load()  # Force image loading
        except Exception as e:
            print(f"Error loading {filename}:{e}")
            return
        if w:
            for warn in w:
# ICCP warning filter
                if "iCCP" in str(warn.message) or "cHRM" in str(warn.message):
                    print(f"{filename} warning:{warn.message}")
                else:
                 print(f"{filename}-no warnings.")

# Change the directory as per your need.
image_dir="user_images/"
for file in os.listdir(image_dir):
    if file.lower().endswith(".png"):
        check_png(os.path.join(image_dir,file))