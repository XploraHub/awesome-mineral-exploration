"""Weekly check of the 18-month rule.

Lists active tools whose repository has had no push for 18 months, and
archived tools that have been pushed to again, in one issue. Closes the
issue when there is nothing to move.
"""

import datetime
import json
import re
import subprocess

TITLE = "Tools to move (18-month rule)"
REPO = re.compile(r"^- \[([^\]]+)\]\(https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\)", re.M)


def gh(*args):
    return subprocess.run(["gh", *args], capture_output=True, text=True)


def section(text, start, end):
    return text[text.index(start):text.index(end)]


def last_push(repo):
    result = gh("api", f"repos/{repo}", "--jq", ".pushed_at")
    return result.stdout.strip()[:10] if result.returncode == 0 else None


readme = open("README.md", encoding="utf-8").read()
active = REPO.findall(readme[:readme.index("## Related lists")])
archived = REPO.findall(section(readme, "## No longer maintained", "## Contributing"))
cutoff = (datetime.date.today() - datetime.timedelta(days=548)).isoformat()

stale, revived, unknown = [], [], []
for name, repo in active:
    pushed = last_push(repo)
    if pushed is None:
        unknown.append(f"- [{name}](https://github.com/{repo})")
    elif pushed < cutoff:
        stale.append(f"- [{name}](https://github.com/{repo}): last push {pushed}")
for name, repo in archived:
    pushed = last_push(repo)
    if pushed and pushed >= cutoff:
        revived.append(f"- [{name}](https://github.com/{repo}): last push {pushed}")

parts = []
if stale:
    parts.append("Move to **No longer maintained** (no push since before " + cutoff + "):\n\n" + "\n".join(stale))
if revived:
    parts.append("Move back to their sections (pushed to again):\n\n" + "\n".join(revived))
if unknown:
    parts.append("Could not be checked (moved, renamed or deleted?):\n\n" + "\n".join(unknown))

found = gh("issue", "list", "--state", "open", "--search", f'in:title "{TITLE}"', "--json", "number,title")
issues = [i["number"] for i in json.loads(found.stdout or "[]") if i["title"] == TITLE]

if parts:
    body = "\n\n".join(parts) + "\n\nSee [CONTRIBUTING.md](CONTRIBUTING.md) for how to move an entry. This issue is updated every week."
    if issues:
        gh("issue", "edit", str(issues[0]), "--body", body)
    else:
        gh("issue", "create", "--title", TITLE, "--body", body)
    print(body)
else:
    for number in issues:
        gh("issue", "close", str(number), "--comment", "Nothing to move this week.")
    print("Nothing to move.")
