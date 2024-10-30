from PIL import Image, ImageDraw, ImageFont
import os

def create_instruction_image(title, instructions, output_path):
    # Create a new image with a white background
    width = 800
    height = 400
    image = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(image)
    
    # Use default font since we can't guarantee specific fonts
    font = ImageFont.load_default()
    
    # Draw title
    draw.text((20, 20), title, fill='black', font=font)
    
    # Draw instructions
    y_position = 60
    for line in instructions:
        draw.text((20, y_position), line, fill='black', font=font)
        y_position += 30
        
    # Ensure the assets directory exists
    os.makedirs('assets', exist_ok=True)
    
    # Save the image
    image.save(output_path)

# Create LinkedIn instructions image
linkedin_instructions = [
    "1. Go to LinkedIn.com and sign in",
    "2. Click on 'My Network'",
    "3. Click on 'Connections'",
    "4. Click on 'Manage Sync and Export Options'",
    "5. Select 'Export Connections'",
    "6. Download your connections as CSV"
]

# Create Notion instructions image
notion_instructions = [
    "1. Go to notion.so/my-integrations",
    "2. Click 'Create new integration'",
    "3. Name your integration",
    "4. Copy the Integration Token",
    "5. Create a new database in Notion",
    "6. Copy the database ID from the URL"
]

create_instruction_image("How to Export LinkedIn Contacts", linkedin_instructions, "assets/howto-linkedin.png")
create_instruction_image("How to Set Up Notion Integration", notion_instructions, "assets/howto-notion.png")
