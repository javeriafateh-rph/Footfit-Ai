"""
vto.py — YouCam AI Shoes Virtual Try-On integration (Perfect Corp / YouCam API)

Flow (per their documented workflow):
1. Upload the user's selfie -> get a src_file_id (or just pass a public src_file_url)
2. Have a public shoe product image URL -> ref_file_url (or upload -> ref_file_id)
3. POST /s2s/v2.0/task/shoes with src + ref + gender + style -> get task_id
4. GET /s2s/v2.0/task/shoes/{task_id} repeatedly until task_status == "success"
5. Read the result image URL out of the response

SETUP REQUIRED (not included here, must be done by you):
1. Register at https://yce.perfectcorp.com/ai-api and redeem your hackathon
   code for 1,000 free API units.
2. Get your API key from https://yce.perfectcorp.com/api-console/en/api-keys/
3. Put it in .streamlit/secrets.toml (NOT committed to git):
       YOUCAM_API_KEY = "your_key_here"
4. On Streamlit Cloud: Settings -> Secrets -> paste the same line.

I could not test this live against Perfect Corp's servers from this
environment (network access here is restricted to package registries, not
arbitrary third-party APIs) — but the response shape below has since been
CONFIRMED against a real Playground test run (Aug 2026):
    {
      "status": 200,
      "data": {
        "error": null,
        "results": { "url": "https://yce-us.s3-accelerate.amazonaws.com/..." },
        "task_status": "success"
      }
    }
The result image URL is at data.results.url — poll_tryon_task() below reads
it from exactly that path. This is a signed, time-limited S3 URL (expires
~2 hours per the X-Amz-Expires param) — display or download it promptly,
don't store the raw URL long-term.

The upload_image() file-endpoint field names (file_id / url) are still
unverified — confirm those against the Playground too if your try-on
requests fail specifically at the upload step rather than the poll step.
"""

import io
import time
import requests
import streamlit as st
from PIL import Image

MIN_DIMENSION = 512  # YouCam's documented minimum: 512x384px, long side ≤4096px
MIN_LONG_SIDE = 512
MAX_LONG_SIDE = 4096

API_BASE = "https://yce-api-01.makeupar.com"
FILE_ENDPOINT = f"{API_BASE}/s2s/v2.0/file/shoes"
TASK_ENDPOINT = f"{API_BASE}/s2s/v2.0/task/shoes"
STYLES = {
    "Random": "random",
    "Minimal Style": "minimal",
    "Boho Style": "boho",
    "Country Style": "country",
    "French Elegance": "french_elegance",
    "Retro": "retro",
}  # confirmed from Playground UI Aug 2026 — internal API values (right column) are best-guess
   # from the display labels; if a call 400s on `style`, check the Playground's generated
   # code snippet for the exact string it sends and correct the values here.


def _api_key():
    try:
        return st.secrets["YOUCAM_API_KEY"]
    except Exception:
        return None


def _ensure_min_size(file_bytes: bytes) -> bytes:
    """
    YouCam's documented requirement is min 512x384px, long side <=4096px.
    A photo picked from a phone gallery or a small product thumbnail can
    easily be smaller than that — and undersized images are a likely cause
    of the API's 500 "Internal Server Error" (the request is well-formed,
    but something in their image pipeline chokes on it). Upscale anything
    too small, and downscale anything absurdly large, before it's sent.
    """
    img = Image.open(io.BytesIO(file_bytes))
    img = img.convert("RGB")
    w, h = img.size
    long_side = max(w, h)

    if long_side < MIN_LONG_SIDE:
        scale = MIN_LONG_SIDE / long_side
        img = img.resize((max(1, round(w * scale)), max(1, round(h * scale))))
    elif long_side > MAX_LONG_SIDE:
        scale = MAX_LONG_SIDE / long_side
        img = img.resize((max(1, round(w * scale)), max(1, round(h * scale))))

    out = io.BytesIO()
    img.save(out, format="JPEG", quality=92)
    return out.getvalue()


def upload_image(file_bytes: bytes, content_type: str = "image/jpeg") -> str:
    """
    Uploads a local image to YouCam using their documented two-step pattern
    (confirmed from Perfect Corp's own FAQ: request an upload URL, then PUT
    the raw bytes to it):
      1. POST /file/shoes with {"files": [{"content_type": ..., "file_name": ...}]}
         -> returns a file_id plus a pre-signed upload URL (and headers to use)
      2. PUT the raw file bytes to that URL with those headers
    Returns the file_id, usable as src_file_id / ref_file_id in a task request.

    This corrects an earlier bug: the very first attempt sent a JSON body
    without a "files" key at all, which is exactly why the API said
    "files is required but wasn't included in your request" — the fix
    is the "files" array below, not a different request style entirely.

    The exact field names for the returned upload URL/headers/file_id are
    still not 100% confirmed against a live success response (Perfect
    Corp's FAQ describes the PUT step but not this response's exact shape)
    — this checks several plausible key names defensively. If it still
    fails, the error message will show the real response so we can adjust.
    """
    api_key = _api_key()
    if not api_key:
        raise RuntimeError("No YOUCAM_API_KEY found in st.secrets.")

    file_bytes = _ensure_min_size(file_bytes)

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"files": [{"content_type": "image/jpeg", "file_name": "image.jpg"}]}
    resp = requests.post(FILE_ENDPOINT, headers=headers, json=payload, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"File request failed ({resp.status_code}): {resp.text}")

    data = resp.json().get("data", {})
    files_list = data.get("files") or [data]  # some APIs return the object directly, not wrapped in a list
    if not files_list:
        raise RuntimeError(f"Unexpected file-request response, please share this: {data}")
    file_info = files_list[0]

    file_id = file_info.get("file_id") or file_info.get("id")
    upload_url = file_info.get("url") or file_info.get("upload_url")
    upload_headers = file_info.get("headers") or {"Content-Type": "image/jpeg"}

    if not file_id or not upload_url:
        raise RuntimeError(f"Unexpected file-request response, please share this: {data}")

    put_resp = requests.put(upload_url, data=file_bytes, headers=upload_headers, timeout=60)
    if put_resp.status_code not in (200, 201, 204):
        raise RuntimeError(f"File upload PUT failed ({put_resp.status_code}): {put_resp.text}")

    return file_id


def _verify_direct_image_url(url: str) -> bool:
    """Confirm a hosted URL actually serves raw image bytes (not an HTML preview page) before trusting it."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=20)
        content_type = resp.headers.get("Content-Type", "")
        return resp.status_code == 200 and content_type.startswith("image")
    except Exception:
        return False


def _host_temporarily(file_bytes: bytes) -> str:
    """
    Uploads an image and returns a public URL for it, so YouCam's
    task/shoes endpoint (confirmed to accept src_file_url / ref_file_url as
    plain URLs) can use it.

    Order: Imgur first (if IMGUR_CLIENT_ID is set — most reliable, built
    for this exact use case), then three free no-signup hosts as fallback.
    Every candidate URL is verified by actually fetching it before it's
    trusted, since we've seen hosts return broken/blocked links that
    LOOK successful but aren't real image content when fetched.
    """
    errors = []

    def _try(name, upload_fn):
        try:
            url = upload_fn()
            if url and _verify_direct_image_url(url):
                return url
            if url:
                errors.append(f"{name}: uploaded but URL didn't verify as a direct image")
            else:
                errors.append(f"{name}: not configured or upload returned nothing")
        except Exception as e:
            errors.append(f"{name}: {e}")
        return None

    ua = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    def _tmpfiles():
        resp = requests.post(
            "https://tmpfiles.org/api/v1/upload",
            files={"file": ("image.jpg", file_bytes, "image/jpeg")},
            headers=ua, timeout=30,
        )
        page_url = resp.json().get("data", {}).get("url", "") if resp.status_code == 200 else ""
        return page_url.replace("tmpfiles.org/", "tmpfiles.org/dl/", 1) if page_url else None

    def _0x0():
        resp = requests.post(
            "https://0x0.st",
            files={"file": ("image.jpg", file_bytes, "image/jpeg")},
            headers=ua, timeout=30,
        )
        text = resp.text.strip()
        return text if resp.status_code == 200 and text.startswith("http") else None

    def _catbox():
        resp = requests.post(
            "https://catbox.moe/user/api.php",
            data={"reqtype": "fileupload"},
            files={"fileToUpload": ("image.jpg", file_bytes, "image/jpeg")},
            headers=ua, timeout=30,
        )
        text = resp.text.strip()
        return text if resp.status_code == 200 and text.startswith("http") else None

    for name, fn in [("tmpfiles.org", _tmpfiles), ("0x0.st", _0x0), ("catbox.moe", _catbox)]:
        result = _try(name, fn)
        if result:
            return result

    raise RuntimeError(f"All image hosts failed: {' | '.join(errors)}")


def start_tryon_task(src_file_id: str = None, ref_file_id: str = None,
                      selfie_url: str = None, shoe_image_url: str = None,
                      gender: str = "female", style: str = "random"):
    """
    Kick off an async try-on task. Either pass uploaded file IDs
    (currently unused — see run_tryon_from_uploads, which hosts files
    publicly and uses URLs instead) or public URLs
    (selfie_url/shoe_image_url) — whichever you have available.
    Returns task_id on success, raises RuntimeError with a readable message on failure.
    """
    api_key = _api_key()
    if not api_key:
        raise RuntimeError(
            "No YOUCAM_API_KEY found in st.secrets. Add it to .streamlit/secrets.toml locally, "
            "and in Streamlit Cloud under Settings > Secrets."
        )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {"gender": gender, "style": style}
    if src_file_id:
        payload["src_file_id"] = src_file_id
    elif selfie_url:
        payload["src_file_url"] = selfie_url
    else:
        raise RuntimeError("Provide either src_file_id or selfie_url.")

    if ref_file_id:
        payload["ref_file_id"] = ref_file_id
    elif shoe_image_url:
        payload["ref_file_url"] = shoe_image_url
    else:
        raise RuntimeError("Provide either ref_file_id or shoe_image_url.")

    resp = requests.post(TASK_ENDPOINT, headers=headers, json=payload, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"Task creation failed ({resp.status_code}): {resp.text}")
    data = resp.json()
    task_id = data.get("data", {}).get("task_id")
    if not task_id:
        raise RuntimeError(f"No task_id in response: {data}")
    return task_id


def poll_tryon_task(task_id: str, max_wait_seconds: int = 60, interval_seconds: int = 3):
    """
    Poll until the task succeeds, fails, or we time out.
    Returns the result image URL on success, raises RuntimeError otherwise.
    """
    api_key = _api_key()
    headers = {"Authorization": f"Bearer {api_key}"}
    url = f"{TASK_ENDPOINT}/{task_id}"

    waited = 0
    while waited < max_wait_seconds:
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code != 200:
            raise RuntimeError(f"Poll failed ({resp.status_code}): {resp.text}")
        data = resp.json().get("data", {})
        status = data.get("task_status")

        if status == "success":
            result_url = data.get("results", {}).get("url")
            if not result_url:
                raise RuntimeError(f"Task succeeded but no result URL found: {data}")
            return result_url
        if status == "error" or data.get("error"):
            raise RuntimeError(f"Task failed: {data}")

        time.sleep(interval_seconds)
        waited += interval_seconds

    raise RuntimeError("Timed out waiting for try-on result. Try again or increase max_wait_seconds.")


def run_tryon_from_uploads(selfie_bytes: bytes, shoe_image_bytes: bytes, gender: str = "female", style: str = "random"):
    """
    Convenience wrapper for two locally-uploaded images.
    Tries YouCam's own native upload endpoint first (upload_image — the
    correct, documented approach). Falls back to the public-hosting
    workaround (_host_temporarily) only if the native path fails, since
    we've confirmed that workaround also genuinely works end-to-end.
    """
    selfie_bytes = _ensure_min_size(selfie_bytes)
    shoe_image_bytes = _ensure_min_size(shoe_image_bytes)

    try:
        src_id = upload_image(selfie_bytes)
        ref_id = upload_image(shoe_image_bytes)
        task_id = start_tryon_task(src_file_id=src_id, ref_file_id=ref_id, gender=gender, style=style)
        return poll_tryon_task(task_id)
    except Exception as native_error:
        try:
            selfie_url = _host_temporarily(selfie_bytes)
            shoe_url = _host_temporarily(shoe_image_bytes)
            task_id = start_tryon_task(selfie_url=selfie_url, shoe_image_url=shoe_url, gender=gender, style=style)
            return poll_tryon_task(task_id)
        except Exception as fallback_error:
            raise RuntimeError(
                f"Native upload failed ({native_error}); fallback hosting also failed ({fallback_error})"
            )


def run_tryon_from_urls(selfie_url: str, shoe_image_url: str, gender: str = "female", style: str = "random"):
    """Convenience wrapper for two public URLs: start task, poll. Use inside a st.spinner()."""
    task_id = start_tryon_task(selfie_url=selfie_url, shoe_image_url=shoe_image_url, gender=gender, style=style)
    return poll_tryon_task(task_id)
