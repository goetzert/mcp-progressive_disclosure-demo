"""Keyword-based tool search for the progressive-disclosure mode.

The search pipeline works as follows:

1.  **Tokenise** the user query and each tool's combined text (name +
    description + parameters) into lowercase alphanumeric tokens.
2.  **Expand** query tokens using :data:`KEYWORD_MAP` — a German→English
    synonym dictionary that bridges language gaps (e.g. ``"wetter"`` →
    ``"weather"``).
3.  **Match** each expanded query token against every tool's token set and
    accumulate a score per tool (one point per matching token).
4.  **Rank** tools by descending score and return the top *k* results.

This module is deliberately dependency-free (uses only :mod:`re`) so it can
be used in both the backend and standalone MCP server contexts.
"""

import re


#: German→English keyword mapping for cross-language tool search.
#:
#: Keys are German terms (lowercase); values are lists of English equivalents
#: that should also be searched.  This allows a German user query like
#: "Wie ist das *Wetter* in Leipzig?" to match English tool names and
#: descriptions such as ``get_weather``.
#:
#: Scoped to terms that actually appear (in translation) in the tool catalog
#: (weather, customers, orders, finance, dummy admin-ops). Identity mappings
#: (e.g. "cache" -> "cache") are omitted since the original query token is
#: always searched anyway (see :func:`_expand_tokens`).
KEYWORD_MAP: dict[str, list[str]] = {
    "wetter": ["weather"],
    "kunde": ["customer"],
    "kunden": ["customer"],
    "bestellung": ["order"],
    "bestellungen": ["order"],
    "auftrag": ["order"],
    "rechnung": ["invoice"],
    "abrechnung": ["invoice"],
    "finanzen": ["finance"],
    "finanziell": ["finance"],
    "temperatur": ["temperature"],
    "luftfeuchtigkeit": ["humidity"],
    "regen": ["precipitation", "rain"],
    "prognose": ["forecast"],
    "steuer": ["tax"],
    "zahlung": ["payment"],
    "bilanz": ["balance"],
    "einkommen": ["income"],
    "ausgaben": ["expenses"],
    "cashflow": ["cash_flow"],
    "datenbank": ["database"],
    "speicher": ["storage"],
    "speicherplatz": ["storage"],
    "warteschlange": ["queue"],
    "dokument": ["document"],
    "benachrichtigung": ["notify"],
    "verschlüsseln": ["encrypt"],
    "entschlüsseln": ["decrypt"],
    "importieren": ["import"],
    "exportieren": ["export"],
    "metriken": ["metrics"],
    "alarm": ["alert"],
    "warnung": ["alert"],
    "warnungen": ["alert"],
    "suche": ["search"],
    "bericht": ["report"],
    "analyse": ["analyze"],
    "erstellen": ["create"],
    "löschen": ["delete"],
    "aktualisieren": ["update"],
    "lieferung": ["deliver", "ship"],
    "stornieren": ["cancel"],
    "qualität": ["quality"],
    "konfiguration": ["config"],
    "neustarten": ["restart"],
    "anhalten": ["pause"],
    "fortsetzen": ["resume"],
    "überwachen": ["monitor"],
    "prüfen": ["check"],
    "validieren": ["validate"],
    "synchronisieren": ["sync"],
    "bereitstellen": ["deploy"],
    "optimieren": ["optimize"],
    "komprimieren": ["compress"],
    "bereinigen": ["clean"],
    "rotieren": ["rotate"],
    "verschmelzen": ["merge"],
    "kommunikation": ["communication"],
    "historie": ["history"],
    "statistiken": ["statistics"],
    "produktpalette": ["inventory"],
}


def _tokenize(text: str) -> list[str]:
    """Split *text* into lowercase alphanumeric tokens (including umlauts)."""
    return re.findall(r"[a-zäöüß0-9]+", text.lower())


def _expand_tokens(tokens: list[str]) -> list[str]:
    """Expand German tokens to their English equivalents via :data:`KEYWORD_MAP`.

    Tokens that have no mapping are kept as-is, so the result always contains
    at least the original tokens.
    """
    expanded = list(tokens)
    for token in tokens:
        if token in KEYWORD_MAP:
            expanded.extend(KEYWORD_MAP[token])
    return expanded


def search(
    query: str,
    tools: list[dict],
    top_k: int = 5,
) -> list[dict]:
    """Search the tool list for tools relevant to *query*.

    The query is tokenised and expanded (German→English) before matching
    against each tool's combined text.  Tools are ranked by the number of
    matching tokens (descending).

    Args:
        query: The user's search query (may be German or English).
        tools: The full list of tool dicts to search within.
        top_k: Maximum number of results to return (default 5).

    Returns:
        A list of up to *top_k* tool dicts, ranked by relevance.
    """
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    query_tokens = _expand_tokens(query_tokens)

    tool_map = {t["name"]: t for t in tools}
    scores: dict[str, float] = {}

    for qt in query_tokens:
        for tool_name in _get_matching_tools(qt, tools):
            scores[tool_name] = scores.get(tool_name, 0) + 1

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [tool_map[name] for name, _ in ranked[:top_k]]


def _get_matching_tools(query_token: str, tools: list[dict]) -> list[str]:
    """Return names of tools whose name or description contains *query_token*.

    Args:
        query_token: A single lowercase token to search for.
        tools: The full list of tool dicts to search within.

    Returns:
        A list of tool names that match the query token.
    """
    matches = []
    for tool in tools:
        name = tool.get("name", "").lower()
        desc = tool.get("description", "").lower()
        if query_token in name or query_token in desc:
            matches.append(tool["name"])
    return matches
