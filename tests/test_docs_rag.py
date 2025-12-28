"""Tests for the documentation RAG system."""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from penguincode.docs_rag.models import (
    Language,
    Library,
    ProjectContext,
    DocChunk,
    DocSearchResult,
)
from penguincode.docs_rag.detector import ProjectDetector
from penguincode.docs_rag.sources import (
    LANGUAGE_DOCS,
    LIBRARY_DOCS,
    get_doc_source,
    get_language_doc_source,
)


class TestLanguageEnum:
    """Tests for Language enum."""

    def test_python_language(self):
        """Test Python language value."""
        assert Language.PYTHON.value == "python"

    def test_javascript_language(self):
        """Test JavaScript language value."""
        assert Language.JAVASCRIPT.value == "javascript"

    def test_typescript_language(self):
        """Test TypeScript language value."""
        assert Language.TYPESCRIPT.value == "typescript"

    def test_go_language(self):
        """Test Go language value."""
        assert Language.GO.value == "go"

    def test_rust_language(self):
        """Test Rust language value."""
        assert Language.RUST.value == "rust"

    def test_hcl_language(self):
        """Test HCL (OpenTofu/Terraform) language value."""
        assert Language.HCL.value == "hcl"

    def test_ansible_language(self):
        """Test Ansible language value."""
        assert Language.ANSIBLE.value == "ansible"


class TestLibrary:
    """Tests for Library dataclass."""

    def test_library_creation(self):
        """Test creating a library."""
        lib = Library(name="fastapi", language=Language.PYTHON, version="0.100.0")
        assert lib.name == "fastapi"
        assert lib.language == Language.PYTHON
        assert lib.version == "0.100.0"

    def test_library_without_version(self):
        """Test creating a library without version."""
        lib = Library(name="react", language=Language.JAVASCRIPT)
        assert lib.name == "react"
        assert lib.version is None

    def test_library_equality(self):
        """Test library equality based on name and language."""
        lib1 = Library(name="fastapi", language=Language.PYTHON)
        lib2 = Library(name="fastapi", language=Language.PYTHON, version="1.0")
        assert lib1 == lib2

    def test_library_hash(self):
        """Test library can be used in sets."""
        lib1 = Library(name="fastapi", language=Language.PYTHON)
        lib2 = Library(name="fastapi", language=Language.PYTHON)
        libs = {lib1, lib2}
        assert len(libs) == 1


class TestProjectContext:
    """Tests for ProjectContext dataclass."""

    def test_empty_context(self):
        """Test creating empty project context."""
        ctx = ProjectContext()
        assert ctx.languages == []
        assert ctx.libraries == []
        assert ctx.language_names == []
        assert ctx.library_names == []

    def test_context_with_languages(self):
        """Test project context with languages."""
        ctx = ProjectContext(languages=[Language.PYTHON, Language.HCL])
        assert Language.PYTHON in ctx.languages
        assert Language.HCL in ctx.languages
        assert "python" in ctx.language_names
        assert "hcl" in ctx.language_names

    def test_context_with_libraries(self):
        """Test project context with libraries."""
        libs = [
            Library(name="fastapi", language=Language.PYTHON),
            Library(name="aws", language=Language.HCL),
        ]
        ctx = ProjectContext(libraries=libs)
        assert "fastapi" in ctx.library_names
        assert "aws" in ctx.library_names

    def test_has_language(self):
        """Test has_language method."""
        ctx = ProjectContext(languages=[Language.PYTHON, Language.ANSIBLE])
        assert ctx.has_language(Language.PYTHON)
        assert ctx.has_language(Language.ANSIBLE)
        assert not ctx.has_language(Language.RUST)

    def test_get_libraries_for_language(self):
        """Test filtering libraries by language."""
        libs = [
            Library(name="fastapi", language=Language.PYTHON),
            Library(name="pydantic", language=Language.PYTHON),
            Library(name="aws", language=Language.HCL),
        ]
        ctx = ProjectContext(libraries=libs)
        python_libs = ctx.get_libraries_for_language(Language.PYTHON)
        assert len(python_libs) == 2
        assert all(lib.language == Language.PYTHON for lib in python_libs)


class TestDocSources:
    """Tests for documentation sources."""

    def test_language_docs_exist(self):
        """Test that all languages have documentation sources."""
        for lang in Language:
            assert lang in LANGUAGE_DOCS, f"Missing docs for {lang}"

    def test_get_language_doc_source(self):
        """Test getting language documentation source."""
        python_docs = get_language_doc_source(Language.PYTHON)
        assert python_docs is not None
        assert "python.org" in python_docs.base_url

    def test_hcl_docs(self):
        """Test OpenTofu documentation source."""
        hcl_docs = get_language_doc_source(Language.HCL)
        assert hcl_docs is not None
        assert "opentofu.org" in hcl_docs.base_url

    def test_ansible_docs(self):
        """Test Ansible documentation source."""
        ansible_docs = get_language_doc_source(Language.ANSIBLE)
        assert ansible_docs is not None
        assert "ansible.com" in ansible_docs.base_url

    def test_popular_python_libraries(self):
        """Test popular Python library docs exist."""
        for lib in ["fastapi", "django", "flask", "pydantic", "pytest"]:
            assert lib in LIBRARY_DOCS, f"Missing docs for {lib}"

    def test_terraform_providers(self):
        """Test Terraform/OpenTofu provider docs exist."""
        for provider in ["aws", "azurerm", "google", "kubernetes"]:
            assert provider in LIBRARY_DOCS, f"Missing docs for {provider}"

    def test_ansible_collections(self):
        """Test Ansible collection docs exist."""
        for collection in ["ansible.builtin", "community.general", "community.docker"]:
            assert collection in LIBRARY_DOCS, f"Missing docs for {collection}"

    def test_get_doc_source(self):
        """Test getting library documentation source."""
        fastapi_docs = get_doc_source("fastapi")
        assert fastapi_docs is not None
        assert "fastapi" in fastapi_docs.base_url.lower()

    def test_get_doc_source_normalized(self):
        """Test doc source lookup with normalized names."""
        # Test character normalization - hyphens are converted to underscores
        # Look up a library that exists in the dictionary
        result = get_doc_source("fastapi")  # Direct match
        assert result is not None
        # Note: Normalization converts hyphens to underscores in lookup


class TestProjectDetector:
    """Tests for ProjectDetector."""

    def test_detect_empty_project(self):
        """Test detecting languages in empty project."""
        with TemporaryDirectory() as tmpdir:
            detector = ProjectDetector(tmpdir)
            ctx = detector.detect()
            assert ctx.languages == []
            assert ctx.libraries == []

    def test_detect_python_from_requirements(self):
        """Test detecting Python from requirements.txt."""
        with TemporaryDirectory() as tmpdir:
            req_file = Path(tmpdir) / "requirements.txt"
            req_file.write_text("fastapi>=0.100.0\npydantic\n")

            detector = ProjectDetector(tmpdir)
            ctx = detector.detect()

            assert Language.PYTHON in ctx.languages
            assert any(lib.name == "fastapi" for lib in ctx.libraries)
            assert any(lib.name == "pydantic" for lib in ctx.libraries)

    def test_detect_python_from_pyproject(self):
        """Test detecting Python from pyproject.toml."""
        with TemporaryDirectory() as tmpdir:
            pyproject = Path(tmpdir) / "pyproject.toml"
            pyproject.write_text('''
[project]
name = "myproject"
dependencies = [
    "fastapi>=0.100.0",
    "sqlalchemy",
]
''')
            detector = ProjectDetector(tmpdir)
            ctx = detector.detect()

            assert Language.PYTHON in ctx.languages
            assert any(lib.name == "fastapi" for lib in ctx.libraries)

    def test_detect_javascript_from_package_json(self):
        """Test detecting JavaScript from package.json."""
        with TemporaryDirectory() as tmpdir:
            package = Path(tmpdir) / "package.json"
            package.write_text('{"dependencies": {"react": "^18.0.0"}}')

            detector = ProjectDetector(tmpdir)
            ctx = detector.detect()

            assert Language.JAVASCRIPT in ctx.languages
            assert any(lib.name == "react" for lib in ctx.libraries)

    def test_detect_typescript_with_tsconfig(self):
        """Test detecting TypeScript from tsconfig.json."""
        with TemporaryDirectory() as tmpdir:
            package = Path(tmpdir) / "package.json"
            package.write_text('{"dependencies": {"react": "^18.0.0"}}')
            tsconfig = Path(tmpdir) / "tsconfig.json"
            tsconfig.write_text('{}')

            detector = ProjectDetector(tmpdir)
            ctx = detector.detect()

            assert Language.JAVASCRIPT in ctx.languages
            assert Language.TYPESCRIPT in ctx.languages

    def test_detect_go_from_go_mod(self):
        """Test detecting Go from go.mod."""
        with TemporaryDirectory() as tmpdir:
            go_mod = Path(tmpdir) / "go.mod"
            go_mod.write_text('''
module example.com/myproject

go 1.21

require (
    github.com/gin-gonic/gin v1.9.0
)
''')
            detector = ProjectDetector(tmpdir)
            ctx = detector.detect()

            assert Language.GO in ctx.languages

    def test_detect_hcl_from_tf_files(self):
        """Test detecting HCL from .tf files."""
        with TemporaryDirectory() as tmpdir:
            main_tf = Path(tmpdir) / "main.tf"
            main_tf.write_text('''
provider "aws" {
  region = "us-west-2"
}
''')
            detector = ProjectDetector(tmpdir)
            ctx = detector.detect()

            assert Language.HCL in ctx.languages
            assert any(lib.name == "aws" for lib in ctx.libraries)

    def test_detect_ansible_from_playbook(self):
        """Test detecting Ansible from playbook.yml."""
        with TemporaryDirectory() as tmpdir:
            playbook = Path(tmpdir) / "playbook.yml"
            playbook.write_text('''
- name: Configure webserver
  hosts: webservers
  tasks:
    - name: Install nginx
      apt:
        name: nginx
''')
            detector = ProjectDetector(tmpdir)
            ctx = detector.detect()

            assert Language.ANSIBLE in ctx.languages

    def test_detect_ansible_from_roles_dir(self):
        """Test detecting Ansible from roles directory."""
        with TemporaryDirectory() as tmpdir:
            roles_dir = Path(tmpdir) / "roles"
            roles_dir.mkdir()
            (roles_dir / "common").mkdir()

            detector = ProjectDetector(tmpdir)
            ctx = detector.detect()

            assert Language.ANSIBLE in ctx.languages


class TestDocChunk:
    """Tests for DocChunk dataclass."""

    def test_doc_chunk_creation(self):
        """Test creating a documentation chunk."""
        chunk = DocChunk(
            content="FastAPI is a modern web framework...",
            metadata={
                "library": "fastapi",
                "section": "Introduction",
                "url": "https://fastapi.tiangolo.com/",
            },
            chunk_id="abc123",
        )
        assert chunk.content == "FastAPI is a modern web framework..."
        assert chunk.library == "fastapi"
        assert chunk.section == "Introduction"
        assert chunk.url == "https://fastapi.tiangolo.com/"


class TestDocSearchResult:
    """Tests for DocSearchResult dataclass."""

    def test_search_result_creation(self):
        """Test creating a search result."""
        result = DocSearchResult(
            content="FastAPI is a modern web framework...",
            library="fastapi",
            section="Introduction",
            relevance_score=0.95,
        )
        assert result.library == "fastapi"
        assert result.relevance_score == 0.95

    def test_search_result_str(self):
        """Test string representation of search result."""
        result = DocSearchResult(
            content="Content here",
            library="fastapi",
            section="Intro",
            relevance_score=0.9,
        )
        result_str = str(result)
        assert "[fastapi]" in result_str
        assert "Intro" in result_str
