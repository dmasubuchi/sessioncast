"""
internal_agent_reasoning tool — forces Chain-of-Thought before key decisions.

CX Agent Studio pattern from Google Cloud Next '26:
"Make the agent think out loud by treating CoT as a tool call."
Accuracy improvement: +8-12% on complex editorial decisions.
"""

from google.adk.tools import BaseTool


class InternalReasoningTool(BaseTool):
    name = "internal_agent_reasoning"
    description = (
        "Call this tool BEFORE making any important editorial decision. "
        "It helps organize your thinking before writing or structuring content. "
        "Pass the specific question or decision you are about to make."
    )

    def run(self, question: str) -> str:
        return (
            f"[Reasoning checkpoint]\n"
            f"Question: {question}\n"
            f"→ Think through: constraints, options, trade-offs, then decide.\n"
            f"→ Proceed to your next step after reasoning is complete."
        )
