"""
Observation layer: interprets tool results for the task engine.

The observer never guesses: it only reports what the tool actually
said, and it never claims an action succeeded when the result says
otherwise.
"""


class AstraObserver:

    def observe(self, result, tool_name=""):
        """Turn a ToolResult into a structured observation."""

        name = tool_name or result.tool or "tool"

        if result.denied:
            summary = result.response or (
                "That action is not permitted."
            )
        elif result.needs_confirmation:
            summary = result.response or "Confirmation requested."
        elif result.success:
            summary = result.response or f"{name} succeeded."
        else:
            summary = result.response or f"{name} failed."

        return {
            "success": result.success,
            "tool": name,
            "summary": summary,
            "observation": summary,
        }

    def interpret(self, result, tool_name=""):
        """Shortcut: return just the natural-language observation."""

        return self.observe(result, tool_name)["observation"]