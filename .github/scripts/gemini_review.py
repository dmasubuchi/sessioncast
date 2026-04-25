"""Gemini PR review script — called by pr-review.yml.

Reads /tmp/pr-diff.txt, calls Vertex AI Gemini 2.5 Pro, writes /tmp/review.md.
Authentication is handled by Workload Identity (google-github-actions/auth).
"""

import os
import sys

import vertexai
from vertexai.generative_models import GenerativeModel

PROMPT_PREFIX = (
    "You are a senior engineer reviewing a pull request for SessionCast, "
    "an AI content pipeline built on Google Cloud "
    "(Vertex AI ADK, Cloud Run, Firebase).\n\n"
    "Review this diff and provide concise feedback on:\n"
    "1. Security issues (critical, must fix)\n"
    "2. Logic bugs (high, should fix)\n"
    "3. Code quality (medium, consider fixing)\n"
    "4. Positive observations\n\n"
    "Diff:\n"
)
PROMPT_SUFFIX = (
    "\n\nFormat your response as markdown. Be concise and actionable.\n"
    'Start with a one-line summary like: "✅ Looks good" or "⚠️ N issues found"'
)


def main() -> None:
    diff = open("/tmp/pr-diff.txt").read()[:15000]
    if not diff.strip():
        print("No relevant diff found.")
        sys.exit(0)

    project = os.environ["GCP_PROJECT"]
    vertexai.init(project=project, location="us-central1")
    model = GenerativeModel("gemini-2.5-pro")

    response = model.generate_content(PROMPT_PREFIX + diff + PROMPT_SUFFIX)
    print(response.text)
    with open("/tmp/review.md", "w") as f:
        f.write(response.text)


if __name__ == "__main__":
    main()
