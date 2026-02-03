"""Smoke test client for the SAM3 WebUI backend.

Run this on the cloud server after starting uvicorn.

Example:
  python smoke_test.py \
    --base-url http://127.0.0.1:8002 \
    --image /path/to/image.jpg \
    --video /path/to/video.mp4 \
    --prompt "person" \
    --bboxes '[[100,100,400,400]]'
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import requests


def poll_job(base_url: str, job_id: str, timeout_sec: int = 600) -> dict:
    t0 = time.time()
    while True:
        r = requests.get(f"{base_url}/api/v1/jobs/{job_id}", timeout=30)
        r.raise_for_status()
        job = r.json()
        if job.get("status") in {"succeeded", "failed"}:
            return job
        if time.time() - t0 > timeout_sec:
            raise TimeoutError(f"job timeout: {job_id}")
        time.sleep(1.0)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8002")
    parser.add_argument("--image")
    parser.add_argument("--video")
    parser.add_argument("--prompt", default="person")
    parser.add_argument("--bboxes", default="[[100,100,400,400]]")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    print("Health:")
    print(requests.get(f"{base_url}/api/v1/health", timeout=30).json())

    if args.image:
        image_path = Path(args.image)
        print("\nImage text segmentation job:")
        with image_path.open("rb") as f:
            resp = requests.post(
                f"{base_url}/api/v1/image/segment/text",
                files={"image": (image_path.name, f, "application/octet-stream")},
                data={"prompt": args.prompt},
                timeout=120,
            )
        resp.raise_for_status()
        job_id = resp.json()["job_id"]
        job = poll_job(base_url, job_id)
        print(json.dumps(job, ensure_ascii=False, indent=2))

        print("\nImage embedding + query job:")
        with image_path.open("rb") as f:
            emb_resp = requests.post(
                f"{base_url}/api/v1/image/embedding",
                files={"image": (image_path.name, f, "application/octet-stream")},
                data={"ttl_sec": 1800},
                timeout=120,
            )
        emb_resp.raise_for_status()
        emb_job = poll_job(base_url, emb_resp.json()["job_id"])
        embedding_id = (emb_job.get("result") or {}).get("meta", {}).get("embedding_id")
        print("embedding_id:", embedding_id)
        if embedding_id:
            q_resp = requests.post(
                f"{base_url}/api/v1/image/query",
                json={"embedding_id": embedding_id, "query": {"type": "text", "prompt": args.prompt}},
                timeout=120,
            )
            q_resp.raise_for_status()
            q_job = poll_job(base_url, q_resp.json()["job_id"])
            print(json.dumps(q_job, ensure_ascii=False, indent=2))

    if args.video:
        video_path = Path(args.video)
        print("\nVideo bbox tracking job:")
        with video_path.open("rb") as f:
            v_resp = requests.post(
                f"{base_url}/api/v1/video/track/bbox",
                files={"video": (video_path.name, f, "application/octet-stream")},
                data={"init_bboxes_json": args.bboxes},
                timeout=300,
            )
        v_resp.raise_for_status()
        v_job = poll_job(base_url, v_resp.json()["job_id"], timeout_sec=3600)
        print(json.dumps(v_job, ensure_ascii=False, indent=2))

        print("\nVideo text tracking job:")
        with video_path.open("rb") as f:
            vt_resp = requests.post(
                f"{base_url}/api/v1/video/track/text",
                files={"video": (video_path.name, f, "application/octet-stream")},
                data={"prompt": args.prompt},
                timeout=300,
            )
        vt_resp.raise_for_status()
        vt_job = poll_job(base_url, vt_resp.json()["job_id"], timeout_sec=3600)
        print(json.dumps(vt_job, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
