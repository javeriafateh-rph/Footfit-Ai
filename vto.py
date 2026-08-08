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

import time
import requests
import streamlit as st

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


def upload_image(file_bytes: bytes, content_type: str = "image/jpeg") -> str:
    """
    Uploads a local image (e.g. from st.file_uploader) to YouCam and returns
    a file_id usable as src_file_id / ref_file_id in a task request.

    This follows the same request-upload-URL -> PUT pattern documented for
    other YouCam endpoints (e.g. AI Face Swap's /s2s/v2.0/file/face-swap).
    Verify field names against the API Playground for /file/shoes before
    your demo — Perfect Corp's file-upload contract is consistent across
    their APIs but hasn't been directly confirmed here for the shoes endpoint.
    """
    api_key = _api_key()
    if not api_key:
        raise RuntimeError("No YOUCAM_API_KEY found in st.secrets.")

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    resp = requests.post(FILE_ENDPOINT, headers=headers, json={"content_type": content_type}, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"File request failed ({resp.status_code}): {resp.text}")
    data = resp.json().get("data", {})
    file_id = data.get("file_id")
    upload_url = data.get("url") or data.get("upload_url")
    if not file_id or not upload_url:
        raise RuntimeError(f"Unexpected file-upload response: {data}")

    put_resp = requests.put(upload_url, data=file_bytes, headers={"Content-Type": content_type}, timeout=60)
    if put_resp.status_code not in (200, 201, 204):
        raise RuntimeError(f"File upload PUT failed ({put_resp.status_code}): {put_resp.text}")

    return file_id


def start_tryon_task(src_file_id: str = None, ref_file_id: str = None,
                      selfie_url: str = None, shoe_image_url: str = None,
                      gender: str = "female", style: str = "random"):
    """
    Kick off an async try-on task. Either pass uploaded file IDs
    (src_file_id/ref_file_id, from upload_image) or public URLs
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
    """Convenience wrapper for two locally-uploaded images: upload both, start task, poll. Use inside a st.spinner()."""
    src_id = upload_image(selfie_bytes)
    ref_id = upload_image(shoe_image_bytes)
    task_id = start_tryon_task(src_file_id=src_id, ref_file_id=ref_id, gender=gender, style=style)
    return poll_tryon_task(task_id)


def run_tryon_from_urls(selfie_url: str, shoe_image_url: str, gender: str = "female", style: str = "random"):
    """Convenience wrapper for two public URLs: start task, poll. Use inside a st.spinner()."""
    task_id = start_tryon_task(selfie_url=selfie_url, shoe_image_url=shoe_image_url, gender=gender, style=style)
    return poll_tryon_task(task_id)
