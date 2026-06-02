"""
Image Node - Fetches and manages images for presentation slides
Uses Unsplash API for topic-relevant images, with Picsum fallback for reliability
"""

import requests
import os
from pathlib import Path
from typing import List, Optional
from outline_node import PresentationState
from urllib.parse import urlencode, quote
import random
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

# Unsplash API 
UNSPLASH_BASE = "https://api.unsplash.com"
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY", "")  

# Picsum.photos API 
PICSUM_BASE = "https://picsum.photos"

def compress_image_for_pptx(image_path: str, max_width: int = 480, quality: int = 40) -> str:
    """
    Aggressively compress image to reduce PPTX file size
    Target: 100-150KB per image (from 2-6MB)
    
    Args:
        image_path: Path to original image
        max_width: Maximum width in pixels (default 480)
        quality: JPEG quality 1-100 (default 40 for very aggressive compression)
    
    Returns:
        Path to compressed image
    """
    try:
        print(f"DEBUG: Compressing image: {image_path}")
        
        original_size_mb = os.path.getsize(image_path) / (1024 * 1024)
        print(f"DEBUG: Original size: {original_size_mb:.2f}MB")
        
        # Open image
        img = Image.open(image_path)
        original_dimensions = f"{img.width}x{img.height}"
        print(f"DEBUG: Original dimensions: {original_dimensions}")
        
        if img.width != max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
            print(f"DEBUG: Resized to {img.width}x{img.height}")
        
        if img.mode in ('RGBA', 'LA', 'P'):
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'RGBA':
                rgb_img.paste(img, mask=img.split()[-1])
            else:
                rgb_img.paste(img)
            img = rgb_img
            print(f"DEBUG: Converted {original_dimensions} mode to RGB")
        
        temp_path = image_path.replace('.jpg', '_temp.jpg')
        img.save(temp_path, 'JPEG', quality=quality, optimize=True)
        
        os.remove(image_path)
        os.rename(temp_path, image_path)
        
        compressed_size_mb = os.path.getsize(image_path) / (1024 * 1024)
        compressed_size_kb = os.path.getsize(image_path) / 1024
        
        if original_size_mb > 0:
            compression_ratio = ((original_size_mb - compressed_size_mb) / original_size_mb * 100)
        else:
            compression_ratio = 0
        
        print(f"DEBUG: ✓ COMPRESSED: {original_size_mb:.2f}MB → {compressed_size_kb:.1f}KB ({compression_ratio:.1f}% reduction)")
        return image_path
        
    except Exception as e:
        print(f"ERROR: Compression failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return image_path

def calculate_image_positions(total_slides: int) -> List[int]:
    """
    Calculate which slide indices should have images based on total slide count
    Level 3 (Size-Based) approach
    
    Returns list of slide indices (0-based) that should get images
    """
    content_slides = total_slides - 2
    
    if content_slides < 5:
        return [total_slides // 2]
    elif content_slides < 10:
        return [total_slides // 3, (2 * total_slides) // 3]
    else:
        return [total_slides // 4, total_slides // 2, (3 * total_slides) // 4]

def extract_keywords(text: str) -> str:
    """
    Extract meaningful keywords from slide title for image search.
    Returns the main topic/keyword to search for.
    Keeps up to 3 meaningful words and preserves original casing
    (so technical abbreviations like VLSI, AI, ML are not lowercased).

    Examples:
    - "VLSI Design Basics" -> "VLSI Design"
    - "Machine Learning Basics" -> "Machine Learning"
    - "Cloud Computing" -> "Cloud Computing"
    """
    if not text:
        return "professional"

    text = text.strip()

    # Remove common filler suffixes/prefixes (case-insensitive)
    filler_suffixes = [' basics', ' overview', ' introduction', ' guide', ' tutorial', ' tips', ' tricks', ' part0', ' part1', ' part2']
    filler_prefixes = ['the ', 'a ', 'an ', 'getting started with ', 'introduction to ']

    lower = text.lower()
    for suffix in filler_suffixes:
        if lower.endswith(suffix):
            text = text[:len(text) - len(suffix)]
            lower = text.lower()
            break
    for prefix in filler_prefixes:
        if lower.startswith(prefix):
            text = text[len(prefix):]
            lower = text.lower()
            break

    # Keep up to 3 meaningful words (length > 2), preserve original casing
    words = [w for w in text.split() if len(w) > 2]

    if words:
        return ' '.join(words[:3])

    return "professional"

def fetch_unsplash_image(keyword: str, slide_index: int = 0) -> Optional[str]:
    """
    Fetch topic-relevant image from Unsplash API
    Returns path to cached image or None if failed/unavailable
    
    Unsplash API: free tier, 50 requests/hour, requires API key
    Set via environment variable: UNSPLASH_ACCESS_KEY
    """
    if not UNSPLASH_ACCESS_KEY:
        print(f"DEBUG: Unsplash API key not set, skipping Unsplash search")
        return None
    
    try:
        search_url = f"{UNSPLASH_BASE}/search/photos"
        params = {
            "query": keyword,
            "per_page": 1,
            "orientation": "landscape",
            "w": 800,
            "h": 600,
            "client_id": UNSPLASH_ACCESS_KEY
        }
        
        print(f"DEBUG: Searching Unsplash for '{keyword}'")
        response = requests.get(search_url, params=params, timeout=10)
        
        if response.status_code != 200:
            print(f"DEBUG: Unsplash search failed (status {response.status_code})")
            return None
        
        data = response.json()
        results = data.get('results', [])
        
        if not results:
            print(f"DEBUG: No Unsplash results for '{keyword}'")
            return None
        
        image_data = results[0]
        download_url = image_data.get('urls', {}).get('raw')
        image_id = image_data.get('id', '')
        
        if not download_url:
            print(f"DEBUG: No download URL in Unsplash response")
            return None
        
        print(f"DEBUG: Found Unsplash image: {image_id} for '{keyword}'")
        
        img_response = requests.get(download_url, timeout=15)
        if img_response.status_code != 200:
            print(f"DEBUG: Failed to download Unsplash image")
            return None
        
        cache_dir = Path("image_cache").resolve()
        cache_dir.mkdir(exist_ok=True)
        
        # Include a slug of the keyword in the filename so different
        # searches don't reuse each other's cached photos
        kw_slug = "".join(c if c.isalnum() else "_" for c in keyword.lower())[:30]
        cached_path = cache_dir / f"unsplash_{image_id}_{kw_slug}.jpg"
        
        if cached_path.exists():
            abs_path = str(cached_path.absolute())
            print(f"DEBUG: Using cached Unsplash image: {abs_path}")
            return abs_path
        
        with open(cached_path, 'wb') as f:
            f.write(img_response.content)
        
        abs_path = str(cached_path.absolute())
        file_size = len(img_response.content)
        print(f"✓ Unsplash image cached: {abs_path} ({file_size} bytes)")
        return abs_path
        
    except requests.exceptions.Timeout:
        print(f"DEBUG: Unsplash request timeout")
        return None
    except Exception as e:
        print(f"DEBUG: Unsplash fetch failed: {str(e)}")
        return None

def fetch_picsum_image(slide_index: int, keyword: str = "") -> Optional[str]:
    """
    Fetch a random image from Picsum.photos using slide index as seed
    If keyword provided, generates deterministic seed from keyword for consistency
    Returns path to cached image or None if failed
    
    Picsum.photos: https://picsum.photos/800/600?random={seed}
    - Free service
    - No authentication
    - Very reliable (99.9% uptime)
    - Returns high-quality images
    """
    try:
        
        if keyword:
            seed = abs(hash(keyword.lower())) % 1000
            print(f"DEBUG: Using keyword-based seed: {seed} for '{keyword}'")
        else:
            seed = random.randint(1, 1000)
        
        image_url = f"{PICSUM_BASE}/800/600?random={seed}"
        
        print(f"DEBUG: Fetching image from Picsum for slide {slide_index} with seed {seed}")
        if keyword:
            print(f"DEBUG: Keyword: '{keyword}'")
        print(f"DEBUG: URL: {image_url}")
        
        response = requests.get(image_url, timeout=15, stream=True, allow_redirects=True)
        
        print(f"DEBUG: Picsum response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"ERROR: Picsum returned {response.status_code}")
            return None
        
        image_id = f"picsum_slide_{slide_index}_seed_{seed}"
        
        content_length = len(response.content)
        print(f"DEBUG: Got image from Picsum, size: {content_length} bytes")
        
        if content_length < 1000:
            print(f"DEBUG: Image too small ({content_length} bytes), skipping")
            return None
        
        cached_path = cache_image_from_response(response, image_id)
        if cached_path:
            print(f"DEBUG: ✓ Successfully cached image at {cached_path}")
            return cached_path
        
        return None
        
    except requests.exceptions.Timeout:
        print(f"ERROR: Picsum request timeout for slide {slide_index}")
        return None
    except Exception as e:
        print(f"ERROR: Failed to get image from Picsum: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def fetch_image_smart(slide_index: int, keyword: str = "") -> Optional[str]:
    """
    Smart image fetching: Try Unsplash first (topic-relevant), fallback to Picsum (reliable)
    
    Priority:
    1. Unsplash API with keyword search (if API key available) - BEST relevance
    2. Picsum random images (always available) - Reliable fallback
    """
    if keyword:
        print(f"DEBUG: Trying Unsplash for '{keyword}'...")
        unsplash_path = fetch_unsplash_image(keyword, slide_index)
        if unsplash_path:
            print(f"✓ Got Unsplash image (relevant)")
            return unsplash_path
        else:
            print(f"DEBUG: Unsplash unavailable, falling back to Picsum...")
    
    print(f"DEBUG: Using Picsum as fallback...")
    return fetch_picsum_image(slide_index, keyword)

def cache_image_from_response(response: requests.Response, image_id: str) -> Optional[str]:
    """
    Cache image directly from response object
    Returns absolute path to saved image
    """
    try:
        cache_dir = Path("image_cache").resolve()  
        cache_dir.mkdir(exist_ok=True)
        cached_path = cache_dir / f"{image_id}.jpg"
        
        if cached_path.exists():
            abs_path = str(cached_path.absolute())
            print(f"DEBUG: Using cached image at: {abs_path}")
            return abs_path
        
        with open(cached_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        compress_image_for_pptx(str(cached_path), max_width=600, quality=60)
        
        abs_path = str(cached_path.absolute())
        print(f"DEBUG: Image cached and compressed at {abs_path}")
        return abs_path
        
    except Exception as e:
        print(f"ERROR: Failed to cache image: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def download_and_cache_image(image_url: str, image_id: str) -> Optional[str]:
    """
    Download image from URL and save to cache directory
    Returns absolute path to saved image
    """
    try:
        cache_dir = Path("image_cache").resolve()  
        cache_dir.mkdir(exist_ok=True)
        cached_path = cache_dir / f"{image_id}.jpg"
        
        if cached_path.exists():
            abs_path = str(cached_path.absolute())
            print(f"DEBUG: Using cached image at: {abs_path}")
            return abs_path
        
        print(f"DEBUG: Downloading image from {image_url[:60]}...")
        
        max_retries = 2
        response = None
        for attempt in range(max_retries + 1):
            try:
                response = requests.get(image_url, timeout=15)
                if response.status_code == 200:
                    break
                elif attempt < max_retries:
                    print(f"DEBUG: Download attempt {attempt + 1} failed (status {response.status_code}), retrying...")
                    continue
                else:
                    print(f"ERROR: Failed to download image after {max_retries + 1} attempts, status: {response.status_code}")
                    return None
            except requests.exceptions.Timeout:
                if attempt < max_retries:
                    print(f"DEBUG: Download timeout on attempt {attempt + 1}, retrying...")
                else:
                    print(f"ERROR: Download timeout after {max_retries + 1} attempts")
                    return None
        
        if response is None:
            return None
        
        with open(cached_path, 'wb') as f:
            f.write(response.content)
        
        compress_image_for_pptx(str(cached_path), max_width=600, quality=60)
        
        abs_path = str(cached_path.absolute())
        print(f"DEBUG: Image cached and compressed at {abs_path}")
        return abs_path
        
    except Exception as e:
        print(f"ERROR: Failed to download/cache image: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def fetch_images_node(state: PresentationState) -> PresentationState:
    """
    Fetch images for slides in parallel for speed.
    Uses ThreadPoolExecutor to fetch all images concurrently.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    try:
        slides = state['content'].get('slides', []) if isinstance(state.get('content'), dict) else []

        # Determine image positions and keywords
        if not slides:
            total_slides = state['slide_count'] + 2
            image_slide_indices = calculate_image_positions(total_slides)
            topic_clean = state['topic'].strip()
            words = [w for w in topic_clean.split() if len(w) > 3]
            tasks = []
            for idx, slide_idx in enumerate(image_slide_indices):
                # Use different meaningful words from the topic for variety
                # Fall back to full topic extract if not enough words
                if len(words) > 1 and idx < len(words):
                    kw = words[idx]
                else:
                    kw = extract_keywords(topic_clean)
                tasks.append((slide_idx, kw))
        else:
            total_slides = len(slides) + 2
            image_slide_indices = calculate_image_positions(total_slides)
            tasks = []
            for slide_idx in image_slide_indices:
                content_idx = slide_idx - 1
                if 0 <= content_idx < len(slides):
                    slide_title = slides[content_idx].get('title', f'Slide {slide_idx}')
                    tasks.append((slide_idx, extract_keywords(slide_title)))

        print(f"DEBUG: Fetching {len(tasks)} images in parallel")

        # Fetch all images concurrently
        results = {}  # slide_idx → (path, keyword)
        with ThreadPoolExecutor(max_workers=len(tasks) or 1) as executor:
            future_to_task = {
                executor.submit(fetch_image_smart, slide_idx, kw): (slide_idx, kw)
                for slide_idx, kw in tasks
            }
            for future in as_completed(future_to_task):
                slide_idx, kw = future_to_task[future]
                try:
                    path = future.result()
                    if path:
                        results[slide_idx] = (path, kw)
                        print(f"DEBUG: ✓ Got image for slide {slide_idx}: {kw}")
                    else:
                        print(f"DEBUG: ✗ No image for slide {slide_idx}")
                except Exception as e:
                    print(f"DEBUG: ✗ Image fetch failed for slide {slide_idx}: {e}")

        # Preserve original order
        image_paths = []
        keywords_used = []
        final_indices = []
        for slide_idx, _ in tasks:
            if slide_idx in results:
                path, kw = results[slide_idx]
                image_paths.append(path)
                keywords_used.append(kw)
                final_indices.append(slide_idx)

        state['image_urls'] = image_paths
        state['image_slides'] = final_indices
        state['image_keywords'] = keywords_used

        print(f"DEBUG: Image fetching complete — {len(image_paths)} images fetched")
        return state

    except Exception as e:
        print(f"ERROR in fetch_images_node: {str(e)}")
        import traceback
        traceback.print_exc()
        state['image_urls'] = []
        state['image_slides'] = []
        state['image_keywords'] = []
        return state
