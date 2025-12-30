"""
twitter_watermark_scanner.py

POC: Crawl Twitter/X for images (via snscrape, HTML/Web-based, no official API),
download each image, and verify your invisible watermark by calling your
existing FastAPI endpoint /verify/auto.

Assumptions:
- Your FastAPI app (with the /verify/auto route you posted) is running and reachable.
- You know the correct `owner_email_sha` that was used to register your media_ids.
- PRESETS and verification behavior are configured on the server side.

Usage:
    python twitter_watermark_scanner.py
"""

import logging
import time
from dataclasses import dataclass, field
from typing import List, Set, Dict, Optional

import requests
import snscrape.modules.twitter as sntwitter


# ---------------- CONFIGURATION ---------------- #

@dataclass
class ScannerConfig:
    # Twitter/X sources
    usernames: List[str] = field(default_factory=list)
    hashtags: List[str] = field(default_factory=list)
    max_tweets_per_source: int = 50  # per username / hashtag

    # Watermark verification API
    api_base_url: str = "http://localhost:8000"        # <-- CHANGE THIS if needed
    owner_email_sha: str = ""                          # <-- FILL THIS IN
    preset: Optional[str] = None                       # e.g. "facebook" or None
    use_ecc: bool = True
    ecc_parity_bytes: Optional[int] = None             # usually None to use preset default
    repetition: Optional[int] = None                   # usually None to use preset default
    use_y_channel: Optional[bool] = None               # usually None to use preset default

    # Network / behavior
    request_timeout: int = 15  # seconds for HTTP requests
    sleep_between_sources: float = 1.0  # seconds


# Example config – edit for your POC
CONFIG = ScannerConfig(
    usernames=[
        # add your own / test accounts here
        "AdhikarN36596",
    ],
    hashtags=[
        # e.g. a hashtag you use when testing watermarked uploads
        "klyvo_test",
    ],
    max_tweets_per_source=50,
    api_base_url="http://localhost:8000",  # your FastAPI host/port
    owner_email_sha="8626da84344b864b03cddb094669a771be9f3627d741000625dba5d59b04cb8f",  # <<< IMPORTANT
    preset=None,  # or "facebook" / whatever you use on server
    use_ecc=True,
    ecc_parity_bytes=None,
    repetition=None,
    use_y_channel=None,
)


# ---------------- LOGGING ---------------- #

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


# ---------------- VERIFICATION CALL ---------------- #

def verify_image_with_api(
    image_bytes: bytes,
    filename: str,
    context: Dict
) -> Optional[Dict]:
    """
    Send image bytes to your FastAPI /verify/auto endpoint and get AutoVerifyResult.

    Uses exactly the fields expected by the code you shared:
      - file: UploadFile
      - owner_email_sha: str
      - optional: preset, use_ecc, ecc_parity_bytes, repetition, use_y_channel
    """
    if not CONFIG.owner_email_sha:
        logger.error("CONFIG.owner_email_sha is empty – please set it before running.")
        return None

    url = CONFIG.api_base_url.rstrip("/") + "/verify/auto"

    files = {
        # field name must match: file: UploadFile = File(...)
        "file": (filename, image_bytes, "image/jpeg"),
    }

    data = {
        # required
        "owner_email_sha": CONFIG.owner_email_sha,
        # optional knobs aligned with your endpoint
        "use_ecc": "true" if CONFIG.use_ecc else "false",
    }

    if CONFIG.preset is not None:
        data["preset"] = CONFIG.preset
    if CONFIG.ecc_parity_bytes is not None:
        data["ecc_parity_bytes"] = str(CONFIG.ecc_parity_bytes)
    if CONFIG.repetition is not None:
        data["repetition"] = str(CONFIG.repetition)
    if CONFIG.use_y_channel is not None:
        data["use_y_channel"] = "true" if CONFIG.use_y_channel else "false"

    try:
        resp = requests.post(
            url,
            files=files,
            data=data,
            timeout=CONFIG.request_timeout,
        )
    except Exception as e:
        logger.warning(f"    Error calling verify API: {e}")
        return None

    if resp.status_code != 200:
        logger.warning(f"    Verify API returned {resp.status_code}: {resp.text[:200]}")
        return None

    try:
        result = resp.json()
    except Exception as e:
        logger.warning(f"    Failed to parse JSON response from verify API: {e}")
        return None

    # Optionally enrich with context
    result["_context"] = context
    return result


# ---------------- TWITTER CRAWLING ---------------- #

def process_image_url(image_url: str, context: Dict):
    """
    Download an image URL from Twitter and run your watermark verify API.
    """
    logger.info(f"  [image] {image_url}")
    try:
        r = requests.get(image_url, timeout=CONFIG.request_timeout)
        r.raise_for_status()
        image_bytes = r.content
    except Exception as e:
        logger.warning(f"    Failed to download image: {e}")
        return

    # You can derive a nicer filename if you want
    filename = "twitter_image.jpg"

    # Call your FastAPI verification endpoint
    result = verify_image_with_api(image_bytes, filename, context)
    if not result:
        return

    # AutoVerifyResult fields (from your code):
    # exists: bool
    # ecc_ok: Optional[bool]
    # match_text_hash: Optional[bool]
    # similarity: Optional[float]
    # used_repetition: Optional[int]
    # payload_bits: int
    # owner_email_sha: str
    # matched_media_id: Optional[str]
    # checked_media_ids: int
    # preset: Optional[str]

    if result.get("exists"):
        logger.info("    ✅ WATERMARK DETECTED!")
        logger.info(f"    Result: {result}")
    else:
        logger.info("    ❌ No watermark match (exists = False).")


def crawl_tweets_for_username(username: str, max_tweets: int):
    """
    Crawl tweets for a given username using snscrape (HTML/web-based).
    Only tweets with media (images) will be processed.
    """

    logger.info(f"\n=== Crawling username: @{username} ===")
    query = f"from:{username} has:images"
    tweet_iter = sntwitter.TwitterSearchScraper(query).get_items()

    processed_tweets = 0
    seen_image_urls: Set[str] = set()

    for tweet in tweet_iter:
        if processed_tweets >= max_tweets:
            break

        media_list = getattr(tweet, "media", None)
        if not media_list:
            continue

        image_urls = []
        for media in media_list:
            if hasattr(media, "fullUrl") and media.fullUrl:
                image_urls.append(media.fullUrl)
            elif hasattr(media, "previewUrl") and media.previewUrl:
                image_urls.append(media.previewUrl)

        if not image_urls:
            continue

        processed_tweets += 1
        tweet_url = f"https://x.com/{username}/status/{tweet.id}"

        logger.info(
            f"\n[tweet] @{username} | id={tweet.id} | date={tweet.date} | "
            f"images={len(image_urls)}"
        )
        logger.info(f"  URL: {tweet_url}")

        for idx, url in enumerate(image_urls):
            if url in seen_image_urls:
                continue
            seen_image_urls.add(url)

            context = {
                "source_type": "username",
                "username": username,
                "tweet_id": tweet.id,
                "tweet_date": tweet.date.isoformat(),
                "tweet_url": tweet_url,
                "image_index": idx,
            }
            process_image_url(url, context)

    logger.info(
        f"Finished username @{username}: "
        f"{processed_tweets} tweets with images processed, "
        f"{len(seen_image_urls)} unique image URLs."
    )


def crawl_tweets_for_hashtag(hashtag: str, max_tweets: int):
    """
    Crawl tweets for a given hashtag using snscrape.
    Only tweets with media (images) will be processed.
    """

    logger.info(f"\n=== Crawling hashtag: #{hashtag} ===")
    query = f"#{hashtag} has:images"
    tweet_iter = sntwitter.TwitterSearchScraper(query).get_items()

    processed_tweets = 0
    seen_image_urls: Set[str] = set()

    for tweet in tweet_iter:
        if processed_tweets >= max_tweets:
            break

        media_list = getattr(tweet, "media", None)
        if not media_list:
            continue

        image_urls = []
        for media in media_list:
            if hasattr(media, "fullUrl") and media.fullUrl:
                image_urls.append(media.fullUrl)
            elif hasattr(media, "previewUrl") and media.previewUrl:
                image_urls.append(media.previewUrl)

        if not image_urls:
            continue

        processed_tweets += 1
        username = tweet.user.username if tweet.user else "unknown"
        tweet_url = f"https://x.com/{username}/status/{tweet.id}"

        logger.info(
            f"\n[tweet] #{hashtag} | @{username} | id={tweet.id} | "
            f"date={tweet.date} | images={len(image_urls)}"
        )
        logger.info(f"  URL: {tweet_url}")

        for idx, url in enumerate(image_urls):
            if url in seen_image_urls:
                continue
            seen_image_urls.add(url)

            context = {
                "source_type": "hashtag",
                "hashtag": hashtag,
                "username": username,
                "tweet_id": tweet.id,
                "tweet_date": tweet.date.isoformat(),
                "tweet_url": tweet_url,
                "image_index": idx,
            }
            process_image_url(url, context)

    logger.info(
        f"Finished hashtag #{hashtag}: "
        f"{processed_tweets} tweets with images processed, "
        f"{len(seen_image_urls)} unique image URLs."
    )


def main():
    logger.info("Starting Twitter watermark scanner POC...")

    if not CONFIG.owner_email_sha:
        logger.error("Please set CONFIG.owner_email_sha before running.")
        return

    # Crawl usernames
    for username in CONFIG.usernames:
        crawl_tweets_for_username(username, CONFIG.max_tweets_per_source)
        time.sleep(CONFIG.sleep_between_sources)

    # Crawl hashtags
    for hashtag in CONFIG.hashtags:
        crawl_tweets_for_hashtag(hashtag, CONFIG.max_tweets_per_source)
        time.sleep(CONFIG.sleep_between_sources)

    logger.info("All done.")


if __name__ == "__main__":
    main()
