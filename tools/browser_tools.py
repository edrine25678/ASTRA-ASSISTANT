"""
Browser capabilities: open websites and search the web.

A small seed table covers the sites Astra knows by short name; any
proper domain or full URL also works, so every website never needs
to be hard-coded.
"""

import webbrowser
from urllib.parse import quote

from tools.base import Tool, ToolResult


class OpenUrlTool(Tool):

    name = "open_url"
    description = "Open a website in the default browser"
    parameters = {
        "url": {"type": "str", "required": True}
    }

    # Short name -> full URL.
    KNOWN_SITES = {
        "youtube": "https://www.youtube.com",
        "google": "https://www.google.com",
        "gmail": "https://mail.google.com",
        "chatgpt": "https://chatgpt.com",
        "github": "https://github.com",
    }

    # Short name -> spoken confirmation.
    KNOWN_SITE_NAMES = {
        "youtube": "YouTube",
        "google": "Google",
        "gmail": "Gmail",
        "chatgpt": "ChatGPT",
        "github": "GitHub",
    }

    def resolve(self, target):

        value = (target or "").strip().lower()

        if " " in value:
            return None

        if value.startswith(("http://", "https://")):
            return value

        if value in self.KNOWN_SITES:
            return self.KNOWN_SITES[value]

        if "." in value:
            return "https://" + value

        return None

    def validate(self, arguments):

        url = arguments.get("url")

        if not url:
            return "Missing required argument(s): url"

        if self.resolve(url) is None:
            return f"Cannot resolve URL: {url}"

        return None

    def run(self, arguments):

        target = (arguments.get("url") or "").strip().lower()

        url = self.resolve(target)

        webbrowser.open(url)

        if target in self.KNOWN_SITE_NAMES:

            response = f"Opening {self.KNOWN_SITE_NAMES[target]}."

        else:

            host = url.split("//", 1)[1].split("/", 1)[0]

            response = f"Opening {host}."

        return ToolResult(
            success=True,
            data={"url": url},
            response=response,
        )


class SearchWebTool(Tool):

    name = "search_web"
    description = "Search the web with a search engine"
    parameters = {
        "query": {"type": "str", "required": True},
        "engine": {"type": "str"},
    }

    ENGINES = {
        "google": "https://www.google.com/search?q={}",
        "bing": "https://www.bing.com/search?q={}",
        "duckduckgo": "https://duckduckgo.com/?q={}",
        "youtube": "https://www.youtube.com/results?search_query={}",
    }

    def validate(self, arguments):

        error = super().validate(arguments)

        if error:
            return error

        engine = arguments.get("engine") or "google"

        if engine not in self.ENGINES:
            return f"Unknown search engine: {engine}"

        return None

    def run(self, arguments):

        query = (arguments.get("query") or "").strip()

        engine = arguments.get("engine") or "google"

        url = self.ENGINES[engine].format(quote(query))

        webbrowser.open(url)

        return ToolResult(
            success=True,
            data={"engine": engine, "query": query, "url": url},
            response=f"Searching {engine} for {query}.",
        )
