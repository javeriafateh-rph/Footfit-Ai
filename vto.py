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


def _host_temporarily(file_bytes: bytes) -> str:
    """
    Uploads an image to a free, no-signup public file host and returns a
    public URL for it, so YouCam's task/shoes endpoint (which we've
    confirmed accepts src_file_url / ref_file_url as plain URLs) can use it.

    Tries multiple hosts in order and falls back automatically, because
    some of these free services block requests from cloud-hosted servers
    (like Streamlit Cloud) to prevent abuse — catbox.moe returned exactly
    that ("412 Invalid uploader") on a real deployed test. Falling back to
    a different host instead of hard-failing makes this much more reliable
    without needing any API key or signup.
    """
    errors = []

    # Attempt 1: tmpfiles.org
    try:
        resp = requests.post(
            "https://tmpfiles.org/api/v1/upload",
            files={"file": ("image.jpg", file_bytes, "image/jpeg")},
            timeout=30,
        )
        if resp.status_code == 200:
            page_url = resp.json().get("data", {}).get("url", "")
            if page_url:
                # API returns a view page (tmpfiles.org/xxxx/name) — the
                # direct download link needs "/dl/" inserted after the domain.
                return page_url.replace("tmpfiles.org/", "tmpfiles.org/dl/", 1)
        errors.append(f"tmpfiles.org: {resp.status_code} {resp.text[:200]}")
    except Exception as e:
        errors.append(f"tmpfiles.org: {e}")

    # Attempt 2: 0x0.st
    try:
        resp = requests.post(
            "https://0x0.st",
            files={"file": ("image.jpg", file_bytes, "image/jpeg")},
            timeout=30,
        )
        if resp.status_code == 200 and resp.text.strip().startswith("http"):
            return resp.text.strip()
        errors.append(f"0x0.st: {resp.status_code} {resp.text[:200]}")
    except Exception as e:
        errors.append(f"0x0.st: {e}")

    # Attempt 3: catbox.moe (last, since we've seen it get blocked before)
    try:
        resp = requests.post(
            "https://catbox.moe/user/api.php",
            data={"reqtype": "fileupload"},
            files={"fileToUpload": ("image.jpg", file_bytes, "image/jpeg")},
            timeout=30,
        )
        if resp.status_code == 200 and resp.text.strip().startswith("http"):
            return resp.text.strip()
        errors.append(f"catbox.moe: {resp.status_code} {resp.text[:200]}")
    except Exception as e:
        errors.append(f"catbox.moe: {e}")

    raise RuntimeError(f"All temporary image hosts failed: {' | '.join(errors)}")


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
    Convenience wrapper for two locally-uploaded images: host both
    temporarily to get public URLs, start task, poll. Use inside a st.spinner().
    """
    selfie_bytes = _ensure_min_size(selfie_bytes)
    shoe_image_bytes = _ensure_min_size(shoe_image_bytes)
    selfie_url = _host_temporarily(selfie_bytes)
    shoe_url = _host_temporarily(shoe_image_bytes)
    task_id = start_tryon_task(selfie_url=selfie_url, shoe_image_url=shoe_url, gender=gender, style=style)
    return poll_tryon_task(task_id)


def run_tryon_from_urls(selfie_url: str, shoe_image_url: str, gender: str = "female", style: str = "random"):
    """Convenience wrapper for two public URLs: start task, poll. Use inside a st.spinner()."""
    task_id = start_tryon_task(selfie_url=selfie_url, shoe_image_url=shoe_image_url, gender=gender, style=style)
    return poll_tryon_task(task_id)
