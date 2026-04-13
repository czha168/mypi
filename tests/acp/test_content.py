from codepi.acp.content import (
    text_content,
    resource_content,
    diff_content,
    terminal_content,
)


def test_text_content():
    result = text_content("Hello world")
    assert result == {"type": "text", "text": "Hello world"}


def test_text_content_empty():
    result = text_content("")
    assert result == {"type": "text", "text": ""}


def test_resource_content_without_mime():
    result = resource_content("file:///tmp/main.py", "print('hello')")
    assert result == {
        "type": "resource",
        "resource": {"uri": "file:///tmp/main.py", "text": "print('hello')"},
    }


def test_resource_content_with_mime():
    result = resource_content("file:///tmp/main.py", "print('hello')", mime_type="text/x-python")
    assert result == {
        "type": "resource",
        "resource": {
            "uri": "file:///tmp/main.py",
            "text": "print('hello')",
            "mimeType": "text/x-python",
        },
    }


def test_diff_content_with_old_text():
    result = diff_content("/tmp/main.py", "old code", "new code")
    assert result == {
        "type": "diff",
        "path": "/tmp/main.py",
        "oldText": "old code",
        "newText": "new code",
    }


def test_diff_content_with_none_old_text():
    result = diff_content("/tmp/new.py", None, "new file content")
    assert result == {
        "type": "diff",
        "path": "/tmp/new.py",
        "newText": "new file content",
    }
    assert "oldText" not in result


def test_terminal_content():
    result = terminal_content("term_1")
    assert result == {"type": "terminal", "terminalId": "term_1"}
