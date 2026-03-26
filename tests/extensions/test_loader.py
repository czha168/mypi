import pytest
from pathlib import Path
from codepi.extensions.base import Extension
from codepi.extensions.loader import ExtensionLoader


@pytest.fixture
def simple_extension_file(tmp_extensions_dir):
    ext_file = tmp_extensions_dir / "my_ext.py"
    ext_file.write_text("""
from codepi.extensions.base import Extension

class MyExtension(Extension):
    name = "my-extension"
""")
    return ext_file


def test_loader_finds_extension_subclasses(simple_extension_file, tmp_extensions_dir):
    loader = ExtensionLoader(extensions_dir=tmp_extensions_dir)
    loader.load()
    names = [e.name for e in loader.extensions]
    assert "my-extension" in names


def test_loader_ignores_non_extension_files(tmp_extensions_dir):
    (tmp_extensions_dir / "utils.py").write_text("x = 1")
    loader = ExtensionLoader(extensions_dir=tmp_extensions_dir)
    loader.load()
    assert loader.extensions == []


def test_loader_isolates_broken_extension(tmp_extensions_dir):
    (tmp_extensions_dir / "broken.py").write_text("raise ValueError('intentional')")
    loader = ExtensionLoader(extensions_dir=tmp_extensions_dir)
    loader.load()  # Should not raise
    assert loader.extensions == []
