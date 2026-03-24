import pytest
from pathlib import Path


@pytest.fixture
def sample_python_project(tmp_path: Path) -> Path:
    """Create a sample Python project with various symbol types."""
    project = tmp_path / "sample_project"
    project.mkdir()

    (project / "pyproject.toml").write_text("""
[project]
name = "sample"
version = "0.1.0"
""")

    (project / "src").mkdir()
    (project / "src" / "__init__.py").write_text("")

    (project / "src" / "models.py").write_text('''
class User:
    """A user model."""
    def __init__(self, name: str, age: int):
        self.name = name
        self.age = age

    def greet(self) -> str:
        return f"Hello, {self.name}!"

def create_user(name: str, age: int) -> User:
    return User(name, age)
''')

    (project / "src" / "utils.py").write_text('''
from .models import User

def format_user(user: User) -> str:
    return f"{user.name} ({user.age})"

def calculate_years_until_retirement(user: User, retirement_age: int = 65) -> int:
    return retirement_age - user.age
''')

    (project / "src" / "main.py").write_text('''
from .models import User, create_user
from .utils import format_user

def main():
    user = create_user("Alice", 30)
    greeting = user.greet()
    formatted = format_user(user)
    print(greeting)
    print(formatted)

if __name__ == "__main__":
    main()
''')

    return project


@pytest.fixture
def sample_python_with_errors(tmp_path: Path) -> Path:
    """Create a Python file with type errors for diagnostics testing."""
    project = tmp_path / "error_project"
    project.mkdir()

    (project / "pyproject.toml").write_text("""
[project]
name = "error-sample"
version = "0.1.0"
""")

    (project / "src").mkdir()

    (project / "src" / "errors.py").write_text('''
def add_numbers(a: int, b: int) -> int:
    return a + b

result = add_numbers("hello", "world")

undefined_var = some_undefined_function()

class MyClass:
    pass

obj: str = MyClass()
''')

    return project
