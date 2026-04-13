from __future__ import annotations


def text_content(text: str) -> dict:
    return {"type": "text", "text": text}


def resource_content(uri: str, text: str, mime_type: str | None = None) -> dict:
    resource: dict = {"uri": uri, "text": text}
    if mime_type is not None:
        resource["mimeType"] = mime_type
    return {"type": "resource", "resource": resource}


def diff_content(path: str, old_text: str | None, new_text: str) -> dict:
    result: dict = {"type": "diff", "path": path, "newText": new_text}
    if old_text is not None:
        result["oldText"] = old_text
    return result


def terminal_content(terminal_id: str) -> dict:
    return {"type": "terminal", "terminalId": terminal_id}
