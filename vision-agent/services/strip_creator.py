import os
from PIL import Image

def create_vertical_strip(image_paths, output_path, max_width=600):
    """
    Verilen resim dosyası listesini (image_paths) dikey olarak (alt alta) birleştirir
    ve output_path'e kaydeder.
    Maliyet ve işleme süresini optimize etmek için görseller max_width 
    parametresinde belirtilen genişliğe kadar otomatik boyutlandırılır.
    """
    if not image_paths:
        raise ValueError("Image paths list cannot be empty.")

    images = []
    for path in image_paths:
        try:
            img = Image.open(path)
            # Resize image to respect max_width while maintaining aspect ratio
            if img.width > max_width:
                wpercent = (max_width / float(img.width))
                hsize = int((float(img.height) * float(wpercent)))
                img = img.resize((max_width, hsize), Image.Resampling.LANCZOS)
            images.append(img)
        except Exception as e:
            print(f"Warning: Could not open {path}. Error: {e}")

    if not images:
        raise ValueError("No valid images found to create strip.")

    # Calculate total height and max width of the final image (all should be max_width though)
    widths, heights = zip(*(i.size for i in images))
    total_width = max(widths)
    total_height = sum(heights)

    # Create a new image with the calculated dimensions (white background)
    new_im = Image.new('RGB', (total_width, total_height), (255, 255, 255))

    # Paste each image below the previous one
    y_offset = 0
    for im in images:
        # Center horizontally if it's smaller than max_width
        x_offset = (total_width - im.width) // 2
        new_im.paste(im, (x_offset, y_offset))
        y_offset += im.height

    # Save the final vertical strip
    new_im.save(output_path, quality=85)
    print(f"Vertical strip created successfully: {output_path} (W:{total_width}xH:{total_height})")
    
    return output_path
