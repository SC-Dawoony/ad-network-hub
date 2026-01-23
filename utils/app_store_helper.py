"""App Store helper functions for fetching app information from iOS and Android stores"""
import re
import requests
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

# Check if google-play-scraper is available
try:
    from google_play_scraper import app
    PLAY_STORE_AVAILABLE = True
except ImportError:
    PLAY_STORE_AVAILABLE = False
    app = None
    logger.warning("google-play-scraper library is not installed. Android app details fetching will not be available.")


def get_ios_app_details(app_store_url: str) -> Optional[Dict]:
    """Extract app details from App Store URL
    
    Args:
        app_store_url: App Store URL (e.g., https://apps.apple.com/us/app/.../id1234567890)
    
    Returns:
        Dictionary with app details: app_id, name, bundle_id, icon_url, developer, category
        Returns None if app not found
    """
    if not app_store_url:
        return None
    
    # Extract App ID from URL
    match = re.search(r'/id(\d+)', app_store_url)
    if not match:
        raise ValueError("Invalid App Store URL. Expected format: https://apps.apple.com/.../id1234567890")
    
    app_id = match.group(1)
    itunes_url = f"https://itunes.apple.com/lookup?id={app_id}"
    
    try:
        response = requests.get(itunes_url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            result_count = data.get("resultCount", 0)
            
            if result_count == 0:
                logger.warning(f"iOS app not found for App ID: {app_id}")
                return None
            
            result = data["results"][0]
            
            app_details = {
                "app_id": app_id,
                "name": result.get("trackName"),
                "bundle_id": result.get("bundleId"),
                "icon_url": result.get("artworkUrl512") or result.get("artworkUrl100"),
                "developer": result.get("artistName"),
                "category": result.get("primaryGenreName"),
            }
            
            logger.info(f"Successfully fetched iOS app details: {app_details.get('name')}")
            return app_details
        else:
            logger.error(f"iTunes API returned status code: {response.status_code}")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching iOS app details: {str(e)}")
        raise Exception(f"iOS 앱 정보 조회 중 오류 발생: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_ios_app_details: {str(e)}")
        raise Exception(f"오류 발생: {str(e)}")


def get_android_app_details(play_store_url: str) -> Optional[Dict]:
    """Extract app details from Google Play Store URL
    
    Args:
        play_store_url: Google Play Store URL (e.g., https://play.google.com/store/apps/details?id=com.example.app)
    
    Returns:
        Dictionary with app details: package_name, name, icon_url, developer, category
        Returns None if app not found
    """
    if not play_store_url:
        return None
    
    if not PLAY_STORE_AVAILABLE:
        raise Exception("⚠️ google-play-scraper 라이브러리가 설치되지 않았습니다. 'pip install google-play-scraper'로 설치해주세요.")
    
    # Extract package name from URL
    match = re.search(r'id=([a-zA-Z0-9._]+)', play_store_url)
    if not match:
        raise ValueError("Invalid Play Store URL. Expected format: https://play.google.com/store/apps/details?id=com.example.app")
    
    package_name = match.group(1)
    
    try:
        result = app(package_name, lang='en', country='us')
        
        if not result:
            logger.warning(f"Android app not found for package: {package_name}")
            return None
        
        icon_url = result.get("icon") if isinstance(result, dict) else None
        
        app_details = {
            "package_name": package_name,
            "name": result.get("title", "알 수 없음"),
            "icon_url": icon_url,
            "developer": result.get("developer", "-"),
            "category": result.get("genre", "-"),
        }
        
        logger.info(f"Successfully fetched Android app details: {app_details.get('name')}")
        return app_details
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error fetching Android app details: {error_msg}")
        
        if "404" in error_msg or "not found" in error_msg.lower():
            raise Exception(f"앱을 찾을 수 없습니다: {package_name}")
        else:
            raise Exception(f"오류 발생: {error_msg}")


# BigoAds category codes
BIGOADS_CATEGORIES = [
    "GAME_CASINO", "GAME_SPORTS", "GAME_EDUCATIONAL", "GAME_MUSIC", "GAME_SIMULATION",
    "GAME_ROLE_PLAYING", "GAME_ACTION", "GAME_ADVENTURE", "GAME_RACING", "GAME_STRATEGY",
    "GAME_CARD", "GAME_BOARD", "GAME_TRIVIA", "GAME_WORD", "GAME_PUZZLE", "GAME_ARCADE",
    "GAME_CASUAL",
]

# Map Android/Play Store genre keywords to BigoAds GAME_* code
# Order matters: more specific first. Match is case-insensitive.
_ANDROID_TO_BIGOADS_MAP = [
    (["casino", "gambling", "slots"], "GAME_CASINO"),
    (["sports", "sport"], "GAME_SPORTS"),
    (["educational", "education", "learn"], "GAME_EDUCATIONAL"),
    (["music", "rhythm"], "GAME_MUSIC"),
    (["simulation", "simulator", "sim"], "GAME_SIMULATION"),
    (["role playing", "role-playing", "rpg", "roleplay"], "GAME_ROLE_PLAYING"),
    (["action"], "GAME_ACTION"),
    (["adventure", "adventures"], "GAME_ADVENTURE"),
    (["racing", "race"], "GAME_RACING"),
    (["strategy", "strategic"], "GAME_STRATEGY"),
    (["card", "cards"], "GAME_CARD"),
    (["board"], "GAME_BOARD"),
    (["trivia"], "GAME_TRIVIA"),
    (["word", "words"], "GAME_WORD"),
    (["puzzle", "puzzles"], "GAME_PUZZLE"),
    (["arcade"], "GAME_ARCADE"),
    (["casual"], "GAME_CASUAL"),
]


def map_android_category_to_bigoads(android_category: str) -> str:
    """Map Android/Play Store genre to BigoAds category code.
    
    Play Store genre is often like "Game;Action", "Action", "Casual", "Arcade", etc.
    Returns best matching GAME_* code, or GAME_CASUAL as default.
    """
    if not android_category or not isinstance(android_category, str):
        return "GAME_CASUAL"
    
    # Normalize: lowercase, split by ";" (e.g. "Game;Action" -> ["game", "action"])
    parts = [p.strip().lower() for p in android_category.split(";") if p.strip()]
    if not parts:
        return "GAME_CASUAL"
    
    # If first part is "game", prefer second part for matching
    search_text = " ".join(parts[1:] if parts[0] == "game" and len(parts) > 1 else parts)
    
    for keywords, bigoads_code in _ANDROID_TO_BIGOADS_MAP:
        for kw in keywords:
            if kw in search_text:
                logger.info(f"Android category '{android_category}' -> BigoAds {bigoads_code}")
                return bigoads_code
    
    logger.info(f"Android category '{android_category}' -> BigoAds GAME_CASUAL (no match)")
    return "GAME_CASUAL"


# IronSource taxonomy mapping
# Map Android/Play Store genre to IronSource taxonomy (API value format: lowercase with underscores)
# Order matters: more specific first
_ANDROID_TO_IRONSOURCE_TAXONOMY_MAP = [
    # Casino (specific first)
    (["bingo"], "bingo"),
    (["blackjack"], "blackjack"),
    (["poker"], "poker"),
    (["slots"], "slots"),
    (["sports betting"], "sports_betting"),
    (["casino", "gambling"], "other_casino"),
    # Arcade (specific first)
    (["tower defense"], "tower_defense"),
    (["platformer"], "platformer"),
    (["endless runner"], "endless_runner"),
    (["shoot", "fps", "shooter"], "other_shooter"),
    (["arcade", ".io"], "other_arcade"),
    # Puzzle (specific first)
    (["match 3"], "match_3"),
    (["bubble shooter"], "bubble_shooter"),
    (["word", "words"], "word"),
    (["trivia"], "trivia"),
    (["crossword"], "crossword"),
    (["jigsaw"], "jigsaw"),
    (["solitaire"], "solitaire"),
    (["action puzzle"], "action_puzzle"),
    (["puzzle", "puzzles"], "puzzle"),
    # Casual
    (["casual"], "other_casual"),
    # Simulation (specific first)
    (["farming"], "farming"),
    (["cooking", "time management"], "cooking_time_management"),
    (["tycoon", "crafting"], "tycoon_crafting"),
    (["breeding"], "breeding"),
    (["sandbox"], "sandbox"),
    (["idle simulation"], "idle_simulation"),
    (["simulation", "simulator", "sim"], "other_simulation"),
    # RPG (specific first)
    (["mmorpg"], "mmorpg"),
    (["action rpg"], "action_rpg"),
    (["idle rpg"], "idle_rpg"),
    (["puzzle rpg"], "puzzle_rpg"),
    (["turn-based rpg", "turn based rpg"], "turn_based_rpg"),
    (["fighting"], "fighting"),
    (["survival"], "survival"),
    (["role playing", "rpg", "roleplay"], "other_rpg"),
    # Strategy (specific first)
    (["moba"], "moba"),
    (["4x"], "4x_strategy"),
    (["idle strategy"], "idle_strategy"),
    (["build & battle", "build and battle"], "build_battle"),
    (["sync. battler", "sync battler"], "sync_battler"),
    (["strategy", "strategic"], "other_strategy"),
    # Adventure
    (["adventure", "adventures"], "adventures"),
    # Action (IronSource doesn't have pure "Action", use closest match)
    (["action"], "other_arcade"),
    # Racing (specific first)
    (["simulation racing"], "simulation_racing"),
    (["casual racing"], "casual_racing"),
    (["racing", "race"], "other_racing"),
    # Sports (specific first)
    (["casual sports"], "casual_sports"),
    (["licensed sports"], "licensed_sports"),
    (["sports", "sport"], "sports"),
    # Music
    (["music", "rhythm"], "music_band"),
    # Educational
    (["educational", "education", "learn"], "education"),
    # Card/Board
    (["card", "cards"], "non_casino_card_game"),
    (["board"], "board"),
    # Mid-Core
    (["card battler"], "card_battler"),
    (["mid-core", "midcore"], "other_mid_core"),
]


def map_android_category_to_ironsource_taxonomy(android_category: str) -> str:
    """Map Android/Play Store genre to IronSource taxonomy API value.
    
    Play Store genre is often like "Game;Action", "Action", "Casual", "Arcade", etc.
    Returns best matching taxonomy API value (lowercase with underscores), or "other" as default.
    
    Returns:
        IronSource taxonomy API value (e.g., "puzzle", "other_casual", "action_rpg")
    """
    if not android_category or not isinstance(android_category, str):
        return "other"
    
    # Normalize: lowercase, split by ";" (e.g. "Game;Action" -> ["game", "action"])
    parts = [p.strip().lower() for p in android_category.split(";") if p.strip()]
    if not parts:
        return "other"
    
    # If first part is "game", prefer second part for matching
    search_text = " ".join(parts[1:] if parts[0] == "game" and len(parts) > 1 else parts)
    
    for keywords, ironsource_taxonomy in _ANDROID_TO_IRONSOURCE_TAXONOMY_MAP:
        for kw in keywords:
            if kw in search_text:
                logger.info(f"Android category '{android_category}' -> IronSource taxonomy '{ironsource_taxonomy}'")
                return ironsource_taxonomy
    
    logger.info(f"Android category '{android_category}' -> IronSource taxonomy 'other' (no match)")
    return "other"


# TikTok (Pangle) App Category Code mapping
# Map Android/Play Store genre to TikTok App Category Code (integer)
_ANDROID_TO_TIKTOK_CATEGORY_MAP = [
    # Games - specific first
    (["match 3"], 121330),  # Games-Match 3
    (["puzzle", "puzzles"], 121333),  # Games-Puzzle Game
    (["word", "words"], 121337),  # Games-Word
    (["quiz", "trivia"], 121332),  # Games-Quiz Game
    (["card", "cards"], 121343),  # Games-Card
    (["casual card"], 121336),  # Games-Casual-Card Game
    (["merge"], 121329),  # Games-Merge Game
    (["idle"], 121331),  # Games-Idle Game
    (["arcade runner", "endless runner"], 121335),  # Games-Arcade Runner
    (["music", "rhythm"], 121334),  # Games-Music Game
    (["role playing", "rpg", "roleplay"], 121319),  # Games-Role Playing Game
    (["action rpg"], 121319),  # Games-Role Playing Game
    (["strategy", "strategic", "tower defense"], 121320),  # Games-Hardcore-Strategy Game
    (["moba"], 121339),  # Games-MOBA
    (["shooting", "shooter", "fps"], 121323),  # Games-Shooting Game
    (["racing", "race"], 121324),  # Games-Racing Game
    (["sports", "sport"], 121325),  # Games-Sports Game
    (["simulation", "simulator", "sim"], 121326),  # Games-Simulation Game
    (["action"], 121327),  # Games-Action Game
    (["adventure", "adventures"], 121341),  # Games-Adventure
    (["sandbox"], 121342),  # Games-Sandbox
    (["social game"], 121322),  # Games-Social Game
    (["casual"], 121344),  # Games-Others (fallback for casual)
    (["game"], 121315),  # Games-Game Center (general game)
]


def map_android_category_to_tiktok_category(android_category: str) -> int:
    """Map Android/Play Store genre to TikTok App Category Code.
    
    Play Store genre is often like "Game;Action", "Action", "Casual", "Arcade", etc.
    Returns best matching TikTok App Category Code (integer), or 121344 (Games-Others) as default.
    
    Returns:
        TikTok App Category Code (e.g., 121330 for Match 3, 121333 for Puzzle Game)
    """
    if not android_category or not isinstance(android_category, str):
        return 121344  # Games-Others
    
    # Normalize: lowercase, split by ";" (e.g. "Game;Action" -> ["game", "action"])
    parts = [p.strip().lower() for p in android_category.split(";") if p.strip()]
    if not parts:
        return 121344  # Games-Others
    
    # If first part is "game", prefer second part for matching
    search_text = " ".join(parts[1:] if parts[0] == "game" and len(parts) > 1 else parts)
    
    for keywords, tiktok_code in _ANDROID_TO_TIKTOK_CATEGORY_MAP:
        for kw in keywords:
            if kw in search_text:
                logger.info(f"Android category '{android_category}' -> TikTok category code {tiktok_code}")
                return tiktok_code
    
    logger.info(f"Android category '{android_category}' -> TikTok category code 121344 (Games-Others, no match)")
    return 121344  # Games-Others


# Fyber Android Category mapping
# Map Android/Play Store genre to Fyber Android Category (exact string match required)
_ANDROID_TO_FYBER_ANDROID_CATEGORY_MAP = [
    # Games - specific first
    (["arcade", "arcade & action"], "Games - Arcade & Action"),
    (["brain", "puzzle", "puzzles"], "Games - Brain & Puzzle"),
    (["cards", "casino", "gambling"], "Games - Cards & Casino"),
    (["casual"], "Games - Casual"),
    (["racing", "race"], "Games - Racing"),
    (["sports", "sport"], "Games - Sports Games"),
    (["action"], "Games - Arcade & Action"),  # Action falls under Arcade & Action
    (["adventure"], "Adventure"),
    (["board"], "Board"),
    (["card"], "Games - Cards"),
    (["educational", "education"], "Educational"),
    (["family"], "Family"),
    (["music", "rhythm"], "Music Games"),
    (["role playing", "rpg", "roleplay"], "Role Playing"),
    (["simulation", "simulator", "sim"], "Simulation"),
    (["strategy", "strategic"], "Strategy"),
    (["trivia"], "Trivia"),
    (["word", "words"], "Word Games"),
    # Non-gaming categories
    (["books", "reference"], "Books & Reference"),
    (["business"], "Business"),
    (["comics"], "Comics"),
    (["communication"], "Communication"),
    (["entertainment"], "Entertainment"),
    (["finance"], "Finance"),
    (["health", "fitness"], "Health & Fitness"),
    (["lifestyle"], "Lifestyle"),
    (["medical"], "Medical"),
    (["music & audio", "music"], "Music & Audio"),
    (["news", "magazines"], "News & Magazines"),
    (["personalization"], "Personalization"),
    (["photography"], "Photography"),
    (["productivity"], "Productivity"),
    (["shopping"], "Shopping"),
    (["social"], "Social"),
    (["sports"], "Sports"),
    (["tools"], "Tools"),
    (["transportation"], "Transportation"),
    (["travel", "local"], "Travel & Local"),
    (["weather"], "Weather"),
]


def map_android_category_to_fyber_android_category(android_category: str) -> str:
    """Map Android/Play Store genre to Fyber Android Category.
    
    Play Store genre is often like "Game;Action", "Action", "Casual", "Arcade", etc.
    Returns best matching Fyber Android Category (exact string), or "Games - Casual" as default.
    
    Returns:
        Fyber Android Category (e.g., "Games - Casual", "Games - Arcade & Action", "Entertainment")
    """
    if not android_category or not isinstance(android_category, str):
        return "Games - Casual"
    
    # Normalize: lowercase, split by ";" (e.g. "Game;Action" -> ["game", "action"])
    parts = [p.strip().lower() for p in android_category.split(";") if p.strip()]
    if not parts:
        return "Games - Casual"
    
    # If first part is "game", prefer second part for matching
    search_text = " ".join(parts[1:] if parts[0] == "game" and len(parts) > 1 else parts)
    
    for keywords, fyber_category in _ANDROID_TO_FYBER_ANDROID_CATEGORY_MAP:
        for kw in keywords:
            if kw in search_text:
                logger.info(f"Android category '{android_category}' -> Fyber Android category '{fyber_category}'")
                return fyber_category
    
    logger.info(f"Android category '{android_category}' -> Fyber Android category 'Games - Casual' (no match)")
    return "Games - Casual"
