"""Washington State DOT traffic camera integration."""
import requests
import logging
import config
from modules import cache

log = logging.getLogger(__name__)


def _build_camera_url(camera_id: int) -> str:
    """Build the image URL for a WSDOT traffic camera."""
    return f"https://images.wsdot.wa.gov/nw/005vc{camera_id:05d}.jpg"


def _verify_camera(camera_id: int) -> bool:
    """Quick HEAD request to check if camera image is available."""
    try:
        url = _build_camera_url(camera_id)
        r = requests.head(url, timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def get_cameras() -> dict:
    cached = cache.get("wadot_cameras")
    if cached:
        return cached

    cameras = []
    for cam in config.WSDOT_CAMERA_IDS:
        cam_id = cam["id"]
        image_url = _build_camera_url(cam_id)

        # Try the API if we have a key, otherwise use direct image URL
        if config.WSDOT_API_KEY:
            api_url = (
                f"{config.WSDOT_CAMERAS_BASE}/GetCameraAsJson"
                f"?CameraID={cam_id}&AccessCode={config.WSDOT_API_KEY}"
            )
        else:
            api_url = None

        camera_data = {
            "id": cam_id,
            "label": cam["label"],
            "location": cam["location"],
            "image_url": image_url,
            "api_url": api_url,
            "proxy_url": f"/api/cameras/{cam_id}/image",
        }
        cameras.append(camera_data)

    result = {"cameras": cameras, "count": len(cameras)}
    cache.set("wadot_cameras", result, config.CACHE_TTL["cameras"])
    return result


def fetch_camera_image(camera_id: int) -> bytes:
    """Proxy a camera image to avoid mixed-content / CORS issues."""
    url = _build_camera_url(camera_id)
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.content
