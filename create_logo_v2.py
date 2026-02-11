from PIL import Image, ImageDraw
import os

# Create a professional logo icon for "The Chris Effect Inventory System"
# Blue background with white box and checkmark design
width, height = 256, 256
background = (30, 144, 200)  # Professional blue
white = (255, 255, 255)
dark_blue = (20, 100, 150)

img = Image.new('RGB', (width, height), background)
draw = ImageDraw.Draw(img)

# Draw a large white box (representing the package/inventory)
box_margin = 40
box_coords = [(box_margin, box_margin + 30), (width - box_margin, height - box_margin - 20)]
draw.rectangle(box_coords, fill=white, outline=white, width=3)

# Draw flaps coming out (3D effect)
flap_points_left = [(box_margin - 20, box_margin + 30), (box_margin, box_margin + 30), (box_margin, box_margin + 60), (box_margin - 20, box_margin + 80)]
flap_points_right = [(width - box_margin + 20, box_margin + 30), (width - box_margin, box_margin + 30), (width - box_margin, box_margin + 60), (width - box_margin + 20, box_margin + 80)]

draw.polygon(flap_points_left, fill=white, outline=white)
draw.polygon(flap_points_right, fill=white, outline=white)

# Draw a checkmark in the box
check_x_start = 85
check_y_start = 120
check_x_mid = check_x_start + 15
check_y_mid = check_y_start + 25
check_x_end = check_x_start + 50
check_y_end = check_y_start - 20

draw.line([(check_x_start, check_y_mid), (check_x_mid, check_y_mid + 15), (check_x_end, check_y_end)], fill=background, width=5)

# Save as both PNG and ICO
base_dir = os.path.dirname(__file__)
images_dir = os.path.join(base_dir, 'images')
os.makedirs(images_dir, exist_ok=True)

png_path = os.path.join(images_dir, 'logo.png')
ico_path = os.path.join(images_dir, 'logo.ico')

# Save PNG
img.save(png_path, 'PNG')
print(f'✓ Created: {png_path}')

# Save as ICO (multiple sizes for better quality)
sizes = [(16, 16), (32, 32), (64, 64), (128, 128), (256, 256)]
ico_images = []
for size in sizes:
    sized_img = img.resize(size, Image.Resampling.LANCZOS)
    ico_images.append(sized_img)

ico_images[0].save(ico_path, 'ICO', sizes=[size for size in sizes])
print(f'✓ Created: {ico_path}')

print('\n✓ Logo files created successfully!')
print(f'  PNG: {png_path}')
print(f'  ICO: {ico_path}')
print('\nThe app will now display the logo in the title bar when launched.')
