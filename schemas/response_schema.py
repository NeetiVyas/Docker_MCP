from pydantic import BaseModel, Field
from typing import Optional


class BaseToolResponse(BaseModel):
    tool: str
    status: str = "success"

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)


class ErrorResponse(BaseToolResponse):
    status: str = "error"
    error:  str

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)


class ContainerInfo(BaseModel):
    id: str
    name: str
    image: str
    status: str


class ImageInfo(BaseModel):
    id: str
    tags: list[str]
    size_mb: float
    created: str


class NetworkInfo(BaseModel):
    id:     str
    name:   str
    driver: str
    scope:  str


class RestartResult(BaseModel):
    container: str
    status: str                    
    reason: Optional[str] = None


class ListContainersResponse(BaseToolResponse):
    tool: str = "list_containers"
    total: int
    filter: str                     # "running" | "all"
    containers: list[ContainerInfo]


class RunContainerResponse(BaseToolResponse):
    tool: str = "run_container"
    message: str
    container: ContainerInfo


class StopContainerResponse(BaseToolResponse):
    tool: str = "stop_container"
    message: str
    container_id: str


class RemoveContainerResponse(BaseToolResponse):
    tool: str = "remove_container"
    message: str
    container_id: str
    forced: bool


class RestartContainersResponse(BaseToolResponse):
    tool: str = "restart_containers"
    message: str
    results: list[RestartResult]


class DockerInfoResponse(BaseToolResponse):
    tool:  str = "get_docker_info"
    docker_version: str
    os: str
    architecture: str
    total_containers: int
    running: int
    stopped: int
    total_images: int
    memory_limit: int


class ListImagesResponse(BaseToolResponse):
    tool: str = "list_images"
    total:  int
    images: list[ImageInfo]


class PullImageResponse(BaseToolResponse):
    tool: str = "pull_image"
    message: str
    image: ImageInfo


class RemoveImageResponse(BaseToolResponse):
    tool: str = "remove_image"
    message: str
    image: str
    forced:  bool


class BuildImageResponse(BaseToolResponse):
    tool: str = "build_image"
    message: str
    id: str
    tag: str
    build_logs: list[str]


class ListNetworksResponse(BaseToolResponse):
    tool: str = "list_networks"
    total: int
    networks: list[NetworkInfo]


class CreateNetworkResponse(BaseToolResponse):
    tool: str = "create_network"
    message: str
    network: NetworkInfo


class RemoveNetworkResponse(BaseToolResponse):
    tool: str = "remove_network"
    message: str
    network: str


class ConnectNetworkResponse(BaseToolResponse):
    tool: str = "connect_container_to_network"
    message:   str
    container: str
    network: str


class CreateDockerfileResponse(BaseToolResponse):
    tool: str = "create_dockerfile"
    message: str
    path: str
    language: str
    framework: str
    entry: str
    workdir: str
    port: Optional[int] = None


def tool_error(tool_name: str, message: str) -> str:
    return ErrorResponse(tool=tool_name, error=message).to_json()