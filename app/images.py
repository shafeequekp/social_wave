from dotenv import load_dotenv
from imagekitio import ImageKit
import os

load_dotenv()

IMAGEKIT_PRIVATE_KEY = os.getenv("IMAGEKIT_PRIVATE_KEY")
IMAGEKIT_URL = os.getenv("IMAGEKIT_URL")

imagekit = None

if IMAGEKIT_PRIVATE_KEY:
    imagekit = ImageKit(
        private_key=IMAGEKIT_PRIVATE_KEY,
    )

URL_ENDPOINT = IMAGEKIT_URL