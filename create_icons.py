from PIL import Image, ImageDraw

def create_icon(size):
    img = Image.new('RGB', (size, size), color='#2d6a4f')
    draw = ImageDraw.Draw(img)
    text = '🌱'
    draw.text((size//4, size//4), text, fill='white')
    img.save(f'static/icon-{size}.png')
    print(f'icon-{size}.png created!')

create_icon(192)
create_icon(512)