"""Tools — Pluggable Fähigkeiten des Agenten.

Jedes Tool ist eine Klasse die von BaseTool erbt.
Neue Tools: einfach neue Datei in diesem Ordner anlegen.

Registrierung in agent.py:
    from tools.web_search import WebSearchTool
    from tools.send_email import SendEmailTool

    TOOLS = {
        "web_search": WebSearchTool(),
        "send_email": SendEmailTool(),
    }
"""
