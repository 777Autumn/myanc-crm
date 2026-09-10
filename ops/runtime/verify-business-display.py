"""Read-only post-maintenance display check. Python 3.11+; no config output."""
import argparse
import json
from pathlib import Path
import tomllib


def verify(config, expected):
    """Match gateway EffectiveDisplay precedence, not just global defaults."""
    if len(expected) != 6 or len(set(expected)) != 6 or not all(expected):
        raise ValueError("exactly six distinct verified project names required")
    projects = config.get("projects", [])
    for name in expected:
        matches = [p for p in projects if p.get("name") == name]
        if len(matches) != 1:
            raise ValueError("missing or ambiguous verified environment")
        project = matches[0]
        footer = project.get("reply_footer", project.get("display", {}).get(
            "reply_footer", config.get("display", {}).get("reply_footer", True)))
        if footer is not False:
            raise ValueError("a verified environment still enables the reply footer")
        for setting in ("hide_agent_footer", "final_response_only"):
            effective = project.get("display", {}).get(setting, config.get("display", {}).get(setting, False))
            if effective is not True:
                raise ValueError("a verified environment still exposes intermediate text or agent footers")
    return {"verified_environments": 6, "reply_footer": False,
            "hide_agent_footer": True, "final_response_only": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--project", action="append", required=True)
    args = parser.parse_args()
    try:
        result = verify(tomllib.loads(args.config.read_text(encoding="utf-8")), args.project)
    except (OSError, ValueError, TypeError, AttributeError):
        parser.exit(1, "display verification failed; inspect protected configuration locally\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
