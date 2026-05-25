import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://bikepacking.com"
LISTING_URL = f"{BASE_URL}/bikepacking-routes/"

# Editorial roundup pages — routes linked here get the Top Pick badge.
# Add more as you discover them.
EDITORIAL_URLS = [
    f"{BASE_URL}/plan/our-favorite-bikepacking-routes/",
    f"{BASE_URL}/plog/12-most-popular-2025/",
    f"{BASE_URL}/plan/best-bikepacking-routes-usa/",
    f"{BASE_URL}/plan/best-bikepacking-routes-canada/",
    f"{BASE_URL}/plan/best-gravel-bike-routes/",
]

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

REQUEST_DELAY_MIN = 2.0  # seconds between detail page requests
REQUEST_DELAY_MAX = 5.0

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

GEOCODE_CACHE_FILE = ".geocode_cache.json"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
