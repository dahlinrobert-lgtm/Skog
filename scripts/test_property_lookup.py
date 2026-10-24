#!/usr/bin/env python3
"""One-off probe of Min karta's observed registerenhetermedbuffer endpoint.

Usage:
  python scripts/test_property_lookup.py
  python scripts/test_property_lookup.py EAST NORTH

This is an observed internal web-app endpoint, not a documented public API.
Use only a small number of manual tests.
"""
import json
import sys
import uuid
import requests

BASE = "https://minkarta.lantmateriet.se/api/positionsinformation/positionsinformation/registerenhetermedbuffer/v1"

def main():
    east = float(sys.argv[1]) if len(sys.argv) > 1 else 733554.2119081585
    north = float(sys.argv[2]) if len(sys.argv) > 2 else 7078894.089177589
    params = {
        "transactionId": str(uuid.uuid4()),
        "east": east,
        "north": north,
        "buffer": 1,
    }
    headers = {
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Skog-Grasmyr-monitor/0.3 (single-point test)",
        "Referer": "https://minkarta.lantmateriet.se/",
    }
    try:
        response = requests.get(BASE, params=params, headers=headers, timeout=20)
        print("HTTP status:", response.status_code)
        print("Request URL:", response.url)
        response.raise_for_status()
        data = response.json()
        rows = data.get("registerenheter", [])
        result = {
            "coordinate_sweref99tm": {"east": east, "north": north},
            "fastigheter": [
                {
                    "objectText": item.get("objectText"),
                    "registerenhetstyp": item.get("registerenhetstyp"),
                    "objectId": item.get("objectId"),
                }
                for item in rows
            ],
            "fastigheter_count": len(rows),
            "fastigheter_direct": data.get("fastigheter", []),
            "response_keys": list(data.keys()),
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as exc:
        print(json.dumps({"error": str(exc), "coordinate_sweref99tm": {"east": east, "north": north}}, ensure_ascii=False))
        raise

if __name__ == "__main__":
    main()
