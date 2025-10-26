import os
from PIL import Image, ImageDraw

root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ico_path = os.path.join(root, 'static', 'img', 'app.ico')

size = 256
img = Image.new('RGBA', (size, size), (26, 45, 88, 255))  # fundo azul escuro

draw = ImageDraw.Draw(img)
# moldura arredondada
draw.rounded_rectangle([16, 16, size-16, size-16], radius=32, outline=(255, 255, 255, 230), width=12)
# letra M estilizada com linhas grossas
draw.line([(64, 192), (64, 64)], fill=(255, 255, 255, 255), width=18)
draw.line([(64, 64), (128, 160)], fill=(255, 255, 255, 255), width=18)
draw.line([(128, 160), (192, 64)], fill=(255, 255, 255, 255), width=18)
draw.line([(192, 64), (192, 192)], fill=(255, 255, 255, 255), width=18)

img.save(ico_path, format='ICO', sizes=[(256,256),(128,128),(64,64),(48,48),(32,32),(16,16)])
print(f"ICO gerado: {ico_path}")