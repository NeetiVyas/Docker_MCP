# LIST_CONTAINERS_SCHEMA = {
#     "type": "object",
#     "properties": {
#         "show_all": {
#             "type": "boolean",
#             "description": (
#                 "If true → return ALL containers (running, stopped, exited). "
#                 "If false or omitted → return only RUNNING containers. "
#                 "Set true when user says 'all containers', 'show stopped', 'every container'. "
#                 "Set false when user says 'running containers', 'active containers'."
#             )
#         }
#     },      
#     "required": []
# }

# RUN_CONTAINER_SCHEMA = {
#     "type": "object",
#     "properties": {
#         "image": {
#             "type": "string",
#             "description": "Docker image to run. Examples: 'nginx', 'python:3.11', 'ubuntu:22.04'"
#         },
#         "name": {
#             "type": "string",
#             "description": "(Optional) A friendly name for the container, e.g. 'my-web-server'"
#         },
#         "detach": {
#             "type": "boolean",
#             "description": "(Optional) Run in background (true) or wait for it to finish (false). Defaults to true."
#         }
#     },
#     "required": ["image"]   
# }

# STOP_CONTAINER_SCHEMA = {
#     "type": "object",
#     "properties": {
#         "container_id": {
#             "type": "string",
#             "description": "The container name or ID to stop. Use list_containers to find it."
#         }
#     },
#     "required": ["container_id"]
# }

# REMOVE_CONTAINER_SCHEMA = {
#     "type": "object",
#     "properties": {
#         "container_id": {"type": "string", "description": "Container name or ID to remove"},
#         "force":        {"type": "boolean", "description": "Force remove even if running. Default false."}
#     },
#     "required": ["container_id"]
# }

# CREATE_DOCKERFILE_SCHEMA = {
#     "type": "object",
#     "properties": {
#         "project_path": {
#             "type": "string",
#             "description": "Absolute path to your project folder. The tool will scan it and generate a customized Dockerfile. Example: 'D:/projects/my-app'"
#         },
#         "language": {
#             "type": "string",
#             "description": "(Optional) Force a language: 'python', 'node', or 'go'. If omitted, the tool auto-detects from your project files."
#         },
#         "output_path": {
#             "type": "string",
#             "description": "(Optional) Directory where the Dockerfile will be saved. Defaults to the project_path itself."
#         }
#     },
#     "required": ["project_path"]
# }

# GET_DOCKER_INFO_SCHEMA = {
#     "type": "object",
#     "properties": {},
#     "required": []
# }

# LIST_IMAGES_SCHEMA = {
#     "type": "object",
#     "properties": {},
#     "required": []
# }

# REMOVE_CONTAINER_SCHEMA = {
#     "type": "object",
#     "properties": {
#         "container_id": {"type": "string", "description": "Container name or ID to remove"},
#         "force": {"type": "boolean", "description": "Force remove even if running. Default false."}
#     },
#     "required": ["container_id"]
# }

# PULL_IMAGE_SCHEMA = {
#     "type": "object",
#     "properties": {
#         "image": {"type": "string", "description": "Image to pull, e.g. 'nginx', 'python:3.11'"}
#     },
#     "required": ["image"]
# }

# REMOVE_IMAGE_SCHEMA = {
#     "type": "object",
#     "properties": {
#         "image": {"type": "string", "description": "Image name or ID to remove"},
#         "force": {"type": "boolean", "description": "Force remove even if used by containers. Default false."}
#     },
#     "required": ["image"]
# }

# RESTART_CONTAINERS_SCHEMA = {
#     "type": "object",
#     "properties": {
#         "container_ids": {
#             "type": "array",
#             "items": {"type": "string"},
#             "description": "List of container names or IDs to restart. Single container: ['my-app']"
#         }
#     },
#     "required": ["container_ids"]
# }

# BUILD_IMAGE_SCHEMA = {
#     "type": "object",
#     "properties": {
#         "path": {"type": "string", "description": "Absolute path to folder containing the Dockerfile"},
#         "tag":  {"type": "string", "description": "Tag for the built image, e.g. 'my-app:latest'"}
#     },
#     "required": ["path", "tag"]
# }

# LIST_NETWORKS_SCHEMA = {
#     "type": "object",
#     "properties": {},
#     "required": []
# }

# CREATE_NETWORK_SCHEMA = {
#     "type": "object",
#     "properties": {
#         "name":   {"type": "string",  "description": "Name for the new network"},
#         "driver": {"type": "string",  "description": "Network driver: 'bridge' (default), 'host', 'overlay'"}
#     },
#     "required": ["name"]
# }

# REMOVE_NETWORK_SCHEMA = {
#     "type": "object",
#     "properties": {
#         "network_name": {"type": "string", "description": "Network name or ID to remove"}
#     },
#     "required": ["network_name"]
# }

# CONNECT_CONTAINER_TO_NETWORK_SCHEMA = {
#     "type": "object",
#     "properties": {
#         "container_id":  {"type": "string", "description": "Container name or ID"},
#         "network_name":  {"type": "string", "description": "Network name to connect to"}
#     },
#     "required": ["container_id", "network_name"]
# }


from pydantic import BaseModel, Field
from typing import Optional


class ListContainersInput(BaseModel):
    show_all: bool = Field(
        default=False,
        description=(
            "If true → return ALL containers (running, stopped, exited). "
            "If false → return only RUNNING containers. "
            "Set true when user says 'all containers', 'show stopped'. "
            "Set false when user says 'running containers', 'active'."
        )
    )


class RunContainerInput(BaseModel):
    image: str = Field(description="Docker image to run. E.g. 'nginx', 'python:3.11'")
    name: Optional[str] = Field(default=None,  description="Optional container name")
    detach: Optional[bool]= Field(default=True,  description="Run in background (true) or wait (false)")


class StopContainerInput(BaseModel):
    container_id: str = Field(description="Container name or ID to stop")


class RemoveContainerInput(BaseModel):
    container_id: str  = Field(description="Container name or ID to remove")
    force: bool = Field(default=False, description="Force remove even if running")


class RestartContainersInput(BaseModel):
    container_ids: list[str] = Field(description="List of container names or IDs to restart")


class GetDockerInfoInput(BaseModel):
    pass   


class ListImagesInput(BaseModel):
    pass  


class PullImageInput(BaseModel):
    image: str = Field(description="Image to pull, e.g. 'nginx', 'python:3.11'")


class RemoveImageInput(BaseModel):
    image: str = Field(description="Image name or ID to remove")
    force: bool = Field(default=False, description="Force remove even if used by containers")


class BuildImageInput(BaseModel):
    path: str = Field(description="Absolute path to folder containing the Dockerfile")
    tag:  str = Field(description="Tag for the built image, e.g. 'my-app:latest'")


class ListNetworksInput(BaseModel):
    pass    


class CreateNetworkInput(BaseModel):
    name: str = Field(description="Name for the new network")
    driver: str = Field(default="bridge", description="Network driver: 'bridge', 'host', 'overlay'")


class RemoveNetworkInput(BaseModel):
    network_name: str = Field(description="Network name or ID to remove")


class ConnectContainerToNetworkInput(BaseModel):
    container_id: str = Field(description="Container name or ID")
    network_name: str = Field(description="Network name to connect to")


class CreateDockerfileInput(BaseModel):
    project_path: str = Field(description="Absolute path to your project folder")
    language: Optional[str] = Field(default=None, description="Force language: 'python', 'node', 'go'. Auto-detected if omitted.")
    output_path: Optional[str] = Field(default=None, description="Where to save the Dockerfile. Defaults to project_path.")


class CreateDockerIgnoreFileInput(BaseModel):
    project_path: str = Field(description="Absolute path to your project folder")
    language: Optional[str] = Field(default=None, description="Force language: 'python', 'node', 'go'. Auto-detected if omitted.")
    output_path: Optional[str] = Field(default=None, description="Where to save the Dockerfile. Defaults to project_path.")