import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://bikepacking.com"
LISTING_URL = f"{BASE_URL}/bikepacking-routes/"

# Editorial roundup pages — routes linked here get the Top Pick badge.
# Ordered most-recent first so the freshest label wins when a route appears in multiple pieces.
EDITORIAL_URLS = [
    f"{BASE_URL}/plog/12-most-popular-2025/",
    f"{BASE_URL}/plog/our-editors-favorite-rides-of-2024/",
    f"{BASE_URL}/plog/our-editors-favorite-rides-of-2023/",
    f"{BASE_URL}/plog/top-12-articles-of-2023/",
    f"{BASE_URL}/plog/2022-bikepacking-awards-people-and-routes/",
    f"{BASE_URL}/plan/top-12-bikepacking-routes-2021/",
    f"{BASE_URL}/plog/2020-bikepacking-awards-people-routes/",
    f"{BASE_URL}/plog/2019-bikepacking-awards-people-routes/",
    f"{BASE_URL}/plan/our-favorite-bikepacking-routes/",
]

# Human-readable label shown on the Top Pick badge for each editorial piece.
EDITORIAL_LABELS: dict[str, str] = {
    f"{BASE_URL}/plog/12-most-popular-2025/":                        "Most Popular 2025",
    f"{BASE_URL}/plog/our-editors-favorite-rides-of-2024/":          "Best of 2024",
    f"{BASE_URL}/plog/our-editors-favorite-rides-of-2023/":          "Best of 2023",
    f"{BASE_URL}/plog/top-12-articles-of-2023/":                     "Top 12 of 2023",
    f"{BASE_URL}/plog/2022-bikepacking-awards-people-and-routes/":   "Awards 2022",
    f"{BASE_URL}/plan/top-12-bikepacking-routes-2021/":              "Top 12 of 2021",
    f"{BASE_URL}/plog/2020-bikepacking-awards-people-routes/":       "Awards 2020",
    f"{BASE_URL}/plog/2019-bikepacking-awards-people-routes/":       "Awards 2019",
    f"{BASE_URL}/plan/our-favorite-bikepacking-routes/":             "Editors' Favorites",
}

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
