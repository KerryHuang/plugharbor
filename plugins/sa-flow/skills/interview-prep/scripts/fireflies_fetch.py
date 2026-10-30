#!/usr/bin/env python3
"""Fetch Fireflies.ai meeting transcripts via the GraphQL API.

Stdlib-only (urllib) so it runs with bare `python3` — no pip install needed.

API key resolution order:
  1. env  FIREFLIES_API_KEY
  2. file ~/.config/fireflies/config.json  -> {"api_key": "..."}

Usage:
  # List recent meetings (id, title, date) so a human/agent can pick one
  python3 fireflies_fetch.py --list [--limit 10]

  # Fetch ONE meeting's full payload (summary + action_items + sentences)
  python3 fireflies_fetch.py --id <transcript_id>

  # Fetch the most recent meeting's full payload
  python3 fireflies_fetch.py --latest

Output is JSON on stdout. Errors go to stderr with a non-zero exit code:
  2 = no API key configured
  3 = HTTP / network error
  4 = GraphQL returned errors
  5 = no transcripts found
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

ENDPOINT = "https://api.fireflies.ai/graphql"
CONFIG_PATH = os.path.expanduser("~/.config/fireflies/config.json")


def resolve_api_key():
    key = os.environ.get("FIREFLIES_API_KEY")
    if key:
        return key.strip()
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, encoding="utf-8") as f:
                key = json.load(f).get("api_key")
            if key:
                return key.strip()
        except (json.JSONDecodeError, OSError):
            pass
    sys.stderr.write(
        "ERROR: no Fireflies API key. Set env FIREFLIES_API_KEY or write "
        f"{CONFIG_PATH} as {{\"api_key\": \"...\"}} (chmod 600).\n"
    )
    sys.exit(2)


def gql(api_key, query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        sys.stderr.write(f"ERROR: HTTP {e.code} from Fireflies: {detail}\n")
        sys.exit(3)
    except urllib.error.URLError as e:
        sys.stderr.write(f"ERROR: network error reaching Fireflies: {e.reason}\n")
        sys.exit(3)
    if payload.get("errors"):
        sys.stderr.write("ERROR: GraphQL errors: "
                         + json.dumps(payload["errors"], ensure_ascii=False) + "\n")
        sys.exit(4)
    return payload.get("data", {})


LIST_QUERY = """
query Recent($limit: Int) {
  transcripts(limit: $limit) {
    id
    title
    date
    duration
    organizer_email
  }
}
"""

ONE_QUERY = """
query One($id: String!) {
  transcript(id: $id) {
    id
    title
    date
    duration
    organizer_email
    transcript_url
    summary {
      overview
      action_items
      keywords
      bullet_gist
      topics_discussed
    }
    sentences {
      text
      speaker_name
      start_time
      ai_filters {
        task
        question
      }
    }
  }
}
"""


def cmd_list(api_key, limit):
    data = gql(api_key, LIST_QUERY, {"limit": limit})
    rows = data.get("transcripts") or []
    print(json.dumps(rows, ensure_ascii=False, indent=2))


def cmd_one(api_key, transcript_id):
    data = gql(api_key, ONE_QUERY, {"id": transcript_id})
    t = data.get("transcript")
    if not t:
        sys.stderr.write(f"ERROR: no transcript with id {transcript_id}\n")
        sys.exit(5)
    print(json.dumps(t, ensure_ascii=False, indent=2))


def cmd_latest(api_key):
    data = gql(api_key, LIST_QUERY, {"limit": 1})
    rows = data.get("transcripts") or []
    if not rows:
        sys.stderr.write("ERROR: no transcripts found on this account\n")
        sys.exit(5)
    cmd_one(api_key, rows[0]["id"])


def main():
    p = argparse.ArgumentParser(description="Fetch Fireflies transcripts")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--list", action="store_true", help="list recent meetings")
    g.add_argument("--id", help="fetch one meeting by transcript id")
    g.add_argument("--latest", action="store_true", help="fetch the most recent meeting")
    p.add_argument("--limit", type=int, default=10, help="max meetings for --list (max 50)")
    args = p.parse_args()

    api_key = resolve_api_key()
    if args.list:
        cmd_list(api_key, min(args.limit, 50))
    elif args.id:
        cmd_one(api_key, args.id)
    elif args.latest:
        cmd_latest(api_key)


if __name__ == "__main__":
    main()
