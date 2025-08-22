from setuptools import setup, find_packages
import os
import ast
import sys
import importlib.util
import re
from pathlib import Path

# Leer README principal desde la carpeta readme
readme_dir = Path('readme')
main_readme_path = readme_dir / 'README.md'

try:
    with open(main_readme_path, 'r', encoding='utf-8') as f:
        long_description = f.read()
except FileNotFoundError:
    long_description = "Helper - A centralized toolkit for Python developers"

def find_imports_in_file(filepath):
    """
    Parses a Python file and extracts top-level imported packages.
    Returns a set of base package names.
    """
    with open(filepath, "r", encoding="utf-8") as file:
        node = ast.parse(file.read(), filename=filepath)

    imports = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Import):
            for alias in n.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(n, ast.ImportFrom):
            if n.module:
                imports.add(n.module.split(".")[0])
    return imports

def collect_all_imports(target_dir="helper"):
    """
    Walks through all .py files in the target directory and its subdirs,
    collecting all unique imported modules.
    """
    all_imports = set()
    for root, _, files in os.walk(target_dir):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                all_imports.update(find_imports_in_file(path))
                all_imports.discard("sklearn")
    return sorted(all_imports)

# Packages you know are needed from PyPI (standard lib ones serán ignorados por pip)
raw_deps = collect_all_imports()
internal_modules = {"core", "submodules", "helper"}

# Hardcoded whitelist of standard library modules to ignore (Python >=3.8)
def is_stdlib(module_name):
    spec = importlib.util.find_spec(module_name)
    return spec is not None and 'site-packages' not in (spec.origin or '')

# Only include external dependencies
processed_deps = []
for pkg in raw_deps:
    if not is_stdlib(pkg) and pkg not in internal_modules:
        if pkg == 'sklearn':
            processed_deps.append('scikit-learn')
        else:
            processed_deps.append(pkg)

install_requires = processed_deps

LANGUAGES = [
    "af", "sq", "am", "ar", "hy", "as", "ay", "az", "bm", "eu", "be", "bn", "bho", 
    "bs", "bg", "ca", "ceb", "ny", "zh", "co", "hr", "cs", "da", "dv", 
    "doi", "nl", "en", "eo", "et", "ee", "tl", "fi", "fr", "fy", "gl", "ka", "de", 
    "el", "gn", "gu", "ht", "ha", "haw", "iw", "hi", "hmn", "hu", "is", "ig", "ilo", 
    "id", "ga", "it", "ja", "jw", "kn", "kk", "km", "rw", "gom", "ko", "kri", "ku", 
    "ckb", "ky", "lo", "la", "lv", "ln", "lt", "lg", "lb", "mk", "mai", "mg", "ms", 
    "ml", "mt", "mi", "mr", "lus", "mn", "my", "ne", "no", "or", "om", 
    "ps", "fa", "pl", "pt", "pa", "qu", "ro", "ru", "sm", "sa", "gd", "nso", "sr", 
    "st", "sn", "sd", "si", "sk", "sl", "so", "es", "su", "sw", "sv", "tg", "ta", 
    "tt", "te", "th", "ti", "ts", "tr", "tk", "ak", "uk", "ur", "ug", "uz", "vi", 
    "cy", "xh", "yi", "yo", "zu"
]

# Generar automáticamente la lista de archivos de idiomas
lang_files = [f"lang/{lang}.json" for lang in LANGUAGES]

# Obtener todos los archivos README de la carpeta readme
readme_files = []
if readme_dir.exists():
    for file in readme_dir.iterdir():
        if file.is_file() and file.suffix in ['.md', '.txt', '.rst']:
            readme_files.append(f"readme/{file.name}")

setup(
    name="pyhelper-tools-jbhm",
    version="2.0.0",
    description="A centralized toolkit for Python developers",
    author="Juan Braian Hernandez Morani",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    package_data={
        "helper": lang_files + readme_files
    },
    include_package_data=True,
    install_requires=install_requires,
    python_requires=">=3.8"
)