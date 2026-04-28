import os
import json
from config.settings import SUPPORTED_LANGUAGES
from utils.helpers import success, error
from schemas.response_schema import *


def detect_language(project_path: str) -> str | None:

    files = os.listdir(project_path)

    if "requirements.txt" in files or "pyproject.toml" in files or "setup.py" in files:
        return "python"
    if "package.json" in files:
        return "node"
    if "go.mod" in files:
        return "go"

    return None


def find_python_entrypoint(project_path: str) -> dict:
    files = os.listdir(project_path)
    subdirs = [f for f in files if os.path.isdir(os.path.join(project_path, f)) and not f.startswith('.') and f not in ['env', 'venv', '.venv', '__pycache__', 'node_modules']]

    req_path = os.path.join(project_path, "requirements.txt")
    req_content = ""
    if os.path.exists(req_path):
        with open(req_path) as f:
            req_content = f.read().lower()

    is_fastapi  = "fastapi"  in req_content
    is_uvicorn  = "uvicorn"  in req_content or is_fastapi
    is_django   = "django"   in req_content
    is_gunicorn = "gunicorn" in req_content

    if "manage.py" in files or is_django:
        return {
            "framework": "django",
            "cmd": '["python", "manage.py", "runserver", "0.0.0.0:8000"]',
            "port": 8000,
            "entry": "manage.py"
        }
    
    if "app" in subdirs and os.path.exists(os.path.join(project_path, "app", "main.py")):
        if is_fastapi or is_uvicorn:
            return {
                "framework": "fastapi",
                "cmd": '["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]',
                "port": 8000,
                "entry": "app/main.py"
            }
        
    if "src" in subdirs and os.path.exists(os.path.join(project_path, "src", "main.py")):
        if is_fastapi or is_uvicorn:
            return {
                "framework": "fastapi",
                "cmd": '["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]',
                "port": 8000,
                "entry": "src/main.py"
            }
        
    if "main.py" in files:
        if is_fastapi or is_uvicorn:
            return {
                "framework": "fastapi",
                "cmd": '["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]',
                "port": 8000,
                "entry": "main.py"
            }
        
    if "app.py" in files:
        if is_fastapi or is_uvicorn:
            return {
                "framework": "fastapi",
                "cmd": '["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]',
                "port": 8000,
                "entry": "main.py"
            }
        
    
    if "wsgi.py" in files:
        if is_gunicorn:
            return {
                "framework": "gunicorn",
                "cmd": '["gunicorn", "--bind", "0.0.0.0:8000", "wsgi:application"]',
                "port": 8000,
                "entry": "wsgi.py"
            }
 
    py_files = [f for f in files if f.endswith(".py") and not f.startswith("_")]
    if py_files:
        entry = py_files[0]
        return {
            "framework": "plain",
            "cmd": f'["python", "{entry}"]',
            "port": None,
            "entry": entry
        }
 
    return {
        "framework": "plain",
        "cmd": '["python", "main.py"]',
        "port": None,
        "entry": "main.py"
    }


def detect_node_framework(project_path: str) -> dict:
    pkg_file = os.path.join(project_path, "package.json")

    if not os.path.exists(pkg_file):
        return {"name": "plain", "cmd": '["node", "index.js"]', "port": 3000}

    with open(pkg_file) as f:
        pkg = json.load(f)

    all_deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    entry = pkg.get("main", "index.js")

    if "next" in all_deps:
        return {"name": "next.js", "cmd": '["npm", "start"]',        "port": 3000}
    if "express" in all_deps:
        return {"name": "express", "cmd": f'["node", "{entry}"]',    "port": 3000}
    if "fastify" in all_deps:
        return {"name": "fastify", "cmd": f'["node", "{entry}"]',    "port": 3000}

    start_script = pkg.get("scripts", {}).get("start", "")
    if start_script:
        return {"name": "plain",   "cmd": '["npm", "start"]',        "port": 3000}

    return {"name": "plain", "cmd": f'["node", "{entry}"]', "port": 3000}


def generate_python_dockerfile(project_path: str) -> tuple[str, dict]:
    ep = find_python_entrypoint(project_path)
    has_requirements = os.path.exists(os.path.join(project_path, "requirements.txt"))
    has_pyproject    = os.path.exists(os.path.join(project_path, "pyproject.toml"))

    folder_name = os.path.basename(os.path.abspath(project_path))
    workdir = f"/{folder_name}" if folder_name not in [".", ""] else "/app"
    
    port_line = f"\nEXPOSE {ep['port']}" if ep["port"] else ""

    if has_requirements:
        install_block = (
            "# Install dependencies\n"
            "COPY requirements.txt .\n"
            "RUN pip install --no-cache-dir -r requirements.txt"
        )
    elif has_pyproject:
        install_block = (
            "# Install dependencies via pyproject.toml\n"
            "COPY pyproject.toml .\n"
            "RUN pip install --no-cache-dir ."
        )
    else:
        install_block = "# No requirements file found — add requirements.txt if needed"

    content = (
        f"# Auto-generated Dockerfile for Python ({ep['framework']})\n"
        f"# Entry point detected: {ep['entry']}\n"
        f"# Generated by Docker MCP Server\n"
        f"\n"
        f"FROM python:3.11-slim\n"
        f"\n"
        f"WORKDIR {workdir}\n"
        f"\n"
        f"{install_block}\n"
        f"\n"
        f"# Copy all project files\n"
        f"COPY . .\n"
        f"{port_line}\n"
        f"\n"
        f"CMD {ep['cmd']}\n"
    )
 
    return content, {
        "language":  "python",
        "framework": ep["framework"],
        "port":      ep["port"],
        "entry":     ep["entry"],
        "workdir":   workdir,
    }

def generate_node_dockerfile(project_path: str) -> tuple[str, dict]:
    fw = detect_node_framework(project_path)
    files = os.listdir(project_path)
 
    folder_name = os.path.basename(os.path.abspath(project_path))
    workdir = f"/{folder_name}" if folder_name not in [".", ""] else "/app"
 
    if "yarn.lock" in files:
        copy_cmd    = "COPY package.json yarn.lock ./"
        install_cmd = "RUN yarn install --frozen-lockfile"
    elif "pnpm-lock.yaml" in files:
        copy_cmd    = "COPY package.json pnpm-lock.yaml ./"
        install_cmd = "RUN npm install -g pnpm && pnpm install --frozen-lockfile"
    else:
        copy_cmd    = "COPY package*.json ./"
        install_cmd = "RUN npm install"
 
    content = (
        f"# Auto-generated Dockerfile for Node.js ({fw['name']})\n"
        f"# Generated by Docker MCP Server\n"
        f"\n"
        f"FROM node:20-slim\n"
        f"\n"
        f"WORKDIR {workdir}\n"
        f"\n"
        f"# Install dependencies first (better layer caching)\n"
        f"{copy_cmd}\n"
        f"{install_cmd}\n"
        f"\n"
        f"COPY . .\n"
        f"\n"
        f"EXPOSE {fw['port']}\n"
        f"\n"
        f"CMD {fw['cmd']}\n"
    )
    return content, {"language": "node", "framework": fw["name"], "port": fw["port"], "workdir": workdir}


def generate_go_dockerfile(project_path: str) -> tuple[str, dict]:
    module_name = "app"
    go_mod = os.path.join(project_path, "go.mod")
    if os.path.exists(go_mod):
        with open(go_mod) as f:
            first_line = f.readline().strip()
            if first_line.startswith("module "):
                module_name = first_line.split(" ")[1].split("/")[-1]
 
    folder_name = os.path.basename(os.path.abspath(project_path))
    workdir = f"/{folder_name}" if folder_name not in [".", ""] else "/app"
 
    content = (
        f"# Auto-generated Dockerfile for Go\n"
        f"# Module: {module_name}\n"
        f"# Generated by Docker MCP Server\n"
        f"\n"
        f"# Stage 1: Build\n"
        f"FROM golang:1.22 AS builder\n"
        f"\n"
        f"WORKDIR {workdir}\n"
        f"\n"
        f"COPY go.mod go.sum ./\n"
        f"RUN go mod download\n"
        f"\n"
        f"COPY . .\n"
        f"RUN CGO_ENABLED=0 GOOS=linux go build -o {module_name} .\n"
        f"\n"
        f"# Stage 2: Run\n"
        f"FROM alpine:latest\n"
        f"\n"
        f"WORKDIR {workdir}\n"
        f"\n"
        f"COPY --from=builder {workdir}/{module_name} .\n"
        f"\n"
        f'CMD ["./{module_name}"]\n'
    )
    return content, {"language": "go", "framework": "standard", "port": None, "workdir": workdir}


def create_dockerfile(project_path: str, language: str = None, output_path: str = None) -> str:

    if not os.path.exists(project_path):
        return error(f"Project path does not exist: '{project_path}'")

    if not os.path.isdir(project_path):
        return error(f"'{project_path}' is a file, not a folder. Please provide a directory.")

    if language:
        language = language.lower().strip()
        if language not in SUPPORTED_LANGUAGES:
            return error(
                f"Unsupported language '{language}'. "
                f"Choose one of: {', '.join(SUPPORTED_LANGUAGES)}"
            )
    else:
        language = detect_language(project_path)
        if not language:
            return error(
                "Could not auto-detect the language. "
                "No requirements.txt, package.json, or go.mod found. "
                "Please pass the 'language' argument manually."
            )

    if language == "python":
        content, info = generate_python_dockerfile(project_path)
    elif language == "node":
        content, info = generate_node_dockerfile(project_path)
    elif language == "go":
        content, info = generate_go_dockerfile(project_path)

    save_dir = output_path or project_path

    try:
        os.makedirs(save_dir, exist_ok=True)
        dockerfile_path = os.path.join(save_dir, "Dockerfile")

        with open(dockerfile_path, "w") as f:
            f.write(content)

        return success({
            "message":   f"Dockerfile generated for {info['language']} ({info['framework']}) project.",
            "path":      os.path.abspath(dockerfile_path),
            "language":  info["language"],
            "framework": info["framework"],
            "entry":     info.get("entry", "unknown"),
            "workdir":   info.get("workdir", "/app"),
            "port":      info["port"],
        })

    except OSError as e:
        return error(f"Could not write Dockerfile: {str(e)}")