from PIL import Image

img = Image.open("fb_post_download.jpg")
w, h = img.size
scale = 2048 / max(w, h)
new_size = (int(w*scale), int(h*scale))
img_resized = img.resize(new_size, Image.LANCZOS)
img_resized.save("resized_2.png", quality=95)
