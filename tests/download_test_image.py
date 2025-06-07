"""
Script to download the test image for meal upload testing.
This script will download a sample Vietnamese noodle soup (Bun Bo Hue) image.
"""

import os
import sys

import requests

# Test image URL - replace this with a public URL to the noodle soup image
# For now, using a placeholder service
IMAGE_URL = "https://static.toiimg.com/thumb/msid-97423536,width-1280,resizemode-4/97423536.jpg"
LOCAL_PATH = "tests/test_data/noodle_soup.jpg"

def download_image():
    """Download the test image to the local path."""
    # Make sure the directory exists
    os.makedirs(os.path.dirname(LOCAL_PATH), exist_ok=True)
    
    print(f"Downloading image from {IMAGE_URL}")
    
    try:
        response = requests.get(IMAGE_URL, stream=True)
        response.raise_for_status()  # Raise exception for HTTP errors
        
        # Save the image
        with open(LOCAL_PATH, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"Image downloaded successfully to {LOCAL_PATH}")
        print(f"File size: {os.path.getsize(LOCAL_PATH)} bytes")
        
    except Exception as e:
        print(f"Error downloading image: {e}")
        sys.exit(1)

if __name__ == "__main__":
    download_image() 