# from pydantic import BaseModel, Field
# from typing import Optional


# class BaseToolResponse(BaseModel):
#     tool: str
#     status: str = "success"

#     def to_json(self) -> str:
#         return self.model_dump_json(indent=2)


# class ErrorResponse(BaseToolResponse):
#     status: str = "error"
#     error:  str

#     def to_json(self) -> str:
#         return self.model_dump_json(indent=2)


# class ContainerInfo(BaseModel):
#     id: str
#     name: str
#     image: str
#     status: str


# class ImageInfo(BaseModel):
#     id: str
#     tags: list[str]
#     size_mb: float
#     created: str


# class NetworkInfo(BaseModel):
#     id:     str
#     name:   str
#     driver: str
#     scope:  str


# class RestartResult(BaseModel):
#     container: str
#     status: str                    
#     reason: Optional[str] = None


# class ListContainersResponse(BaseToolResponse):
#     tool: str = "list_containers"
#     total: int
#     filter: str                     # "running" | "all"
#     containers: list[ContainerInfo]


# class RunContainerResponse(BaseToolResponse):
#     tool: str = "run_container"
#     message: str
#     container: ContainerInfo


# class StopContainerResponse(BaseToolResponse):
#     tool: str = "stop_container"
#     message: str
#     container_id: str


# class RemoveContainerResponse(BaseToolResponse):
#     tool: str = "remove_container"
#     message: str
#     container_id: str
#     forced: bool


# class RestartContainersResponse(BaseToolResponse):
#     tool: str = "restart_containers"
#     message: str
#     results: list[RestartResult]


# class DockerInfoResponse(BaseToolResponse):
#     tool:  str = "get_docker_info"
#     docker_version: str
#     os: str
#     architecture: str
#     total_containers: int
#     running: int
#     stopped: int
#     total_images: int
#     memory_limit: int


# class ListImagesResponse(BaseToolResponse):
#     tool: str = "list_images"
#     total:  int
#     images: list[ImageInfo]


# class PullImageResponse(BaseToolResponse):
#     tool: str = "pull_image"
#     message: str
#     image: ImageInfo


# class RemoveImageResponse(BaseToolResponse):
#     tool: str = "remove_image"
#     message: str
#     image: str
#     forced:  bool


# class BuildImageResponse(BaseToolResponse):
#     tool: str = "build_image"
#     message: str
#     id: str
#     tag: str
#     build_logs: list[str]


# class ListNetworksResponse(BaseToolResponse):
#     tool: str = "list_networks"
#     total: int
#     networks: list[NetworkInfo]


# class CreateNetworkResponse(BaseToolResponse):
#     tool: str = "create_network"
#     message: str
#     network: NetworkInfo


# class RemoveNetworkResponse(BaseToolResponse):
#     tool: str = "remove_network"
#     message: str
#     network: str


# class ConnectNetworkResponse(BaseToolResponse):
#     tool: str = "connect_container_to_network"
#     message:   str
#     container: str
#     network: str


# class CreateDockerfileResponse(BaseToolResponse):
#     tool: str = "create_dockerfile"
#     message: str


# class CreateDockerignoreResponse(BaseToolResponse):
#     tool:     str = "create_dockerignore"
#     message:  str
    

# def tool_error(tool_name: str, message: str) -> str:
#     return ErrorResponse(tool=tool_name, error=message).to_json()


from pydantic import BaseModel
from typing import Optional, Any
import json


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
    id: str
    name: str
    driver: str
    scope: str


class RestartResult(BaseModel):
    container: str
    status: str
    reason: Optional[str] = None


class BaseToolResponse(BaseModel):
    tool: str
    status: str = "success"
    message: Optional[str] = None
    data: Optional[Any] = None

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    def display(self) -> dict:
        raise NotImplementedError(f"{self.__class__.__name__} must implement display()")


class ErrorResponse(BaseToolResponse):
    tool: str = "error"
    status: str = "error"
    error: str

    def display(self) -> dict:
        return {"status": "error", "message": self.error}


class ListContainersResponse(BaseToolResponse):
    tool: str = "list_containers"
    data: list[ContainerInfo] = []
    filter: str = "running"

    def display(self) -> dict:
        title = f"{len(self.data)} container(s) — {self.filter}"
        if not self.data:
            return {"status": "success", "title": title, "detail": "_No containers found._", "table": None}
        return {
            "status": "success",
            "title": title,
            "detail": None,
            "table": [
                {"Name": c.name, "Image": c.image, "Status": c.status, "ID": c.id[:12]}
                for c in self.data
            ],
        }


class RunContainerResponse(BaseToolResponse):
    tool: str = "run_container"
    data: ContainerInfo

    def display(self) -> dict:
        c = self.data
        return {
            "status": "success",
            "title": self.message,
            "detail": f"**{c.name}** is `{c.status}`  \nImage: `{c.image}` · ID: `{c.id[:12]}`",
            "table": None,
        }


class StopContainerResponse(BaseToolResponse):
    tool: str = "stop_container"
    data: ContainerInfo

    def display(self) -> dict:
        c = self.data
        return {
            "status": "success",
            "title": self.message,
            "detail": f"**{c.name}** · ID: `{c.id[:12]}`",
            "table": None,
        }


class RemoveContainerResponse(BaseToolResponse):
    tool: str = "remove_container"
    data: ContainerInfo
    forced: bool = False

    def display(self) -> dict:
        extra = " _(forced)_" if self.forced else ""
        return {
            "status": "success",
            "title": self.message,
            "detail": f"**{self.data.name}** · ID: `{self.data.id[:12]}`{extra}",
            "table": None,
        }


class RestartContainersResponse(BaseToolResponse):
    tool: str = "restart_containers"
    data: list[RestartResult] = []

    def display(self) -> dict:
        return {
            "status": "success",
            "title": self.message,
            "detail": None,
            "table": [
                {"Container": r.container, "Result": r.status, "Reason": r.reason or "—"}
                for r in self.data
            ],
        }


class DockerInfoResponse(BaseToolResponse):
    tool: str = "get_docker_info"
    data: dict

    def display(self) -> dict:
        d = self.data
        return {
            "status": "success",
            "title": "Docker info",
            "detail": (
                f"**Version** {d['version']} · **OS** {d['os']} · **Arch** {d['architecture']}  \n"
                f"**Containers** {d['containers']} total "
                f"({d['running']} running, {d['stopped']} stopped) · "
                f"**Images** {d['images']} · **RAM** {d['memory_gb']} GB"
            ),
            "table": None,
        }


class ListImagesResponse(BaseToolResponse):
    tool: str = "list_images"
    data: list[ImageInfo] = []

    def display(self) -> dict:
        title = f"{len(self.data)} image(s) locally"
        if not self.data:
            return {"status": "success", "title": title, "detail": "_No images found._", "table": None}
        return {
            "status": "success",
            "title": title,
            "detail": None,
            "table": [
                {
                    "Tag(s)": ", ".join(img.tags),
                    "Size (MB)": img.size_mb,
                    "Created": img.created,
                    "ID": img.id[7:19],
                }
                for img in self.data
            ],
        }


class PullImageResponse(BaseToolResponse):
    tool: str = "pull_image"
    data: ImageInfo

    def display(self) -> dict:
        img = self.data
        return {
            "status": "success",
            "title": self.message,
            "detail": f"Tags: `{'`, `'.join(img.tags)}`  \nSize: **{img.size_mb} MB** · Created: {img.created}",
            "table": None,
        }


class RemoveImageResponse(BaseToolResponse):
    tool: str = "remove_image"
    data: dict  # {image: str, forced: bool}

    def display(self) -> dict:
        extra = " _(forced)_" if self.data.get("forced") else ""
        return {
            "status": "success",
            "title": self.message,
            "detail": f"Image: `{self.data['image']}`{extra}",
            "table": None,
        }


class BuildImageResponse(BaseToolResponse):
    tool: str = "build_image"
    data: dict  # {id: str, tag: str, build_logs: list[str]}

    def display(self) -> dict:
        logs = "\n".join(self.data.get("build_logs", []))
        return {
            "status": "success",
            "title": self.message,
            "detail": f"Tag: `{self.data['tag']}` · ID: `{self.data['id'][7:19]}`\n\n```\n{logs}\n```",
            "table": None,
        }


class ListNetworksResponse(BaseToolResponse):
    tool: str = "list_networks"
    data: list[NetworkInfo] = []

    def display(self) -> dict:
        title = f"{len(self.data)} network(s)"
        if not self.data:
            return {"status": "success", "title": title, "detail": "_No networks found._", "table": None}
        return {
            "status": "success",
            "title": title,
            "detail": None,
            "table": [
                {"Name": n.name, "Driver": n.driver, "Scope": n.scope, "ID": n.id[:12]}
                for n in self.data
            ],
        }


class CreateNetworkResponse(BaseToolResponse):
    tool: str = "create_network"
    data: NetworkInfo

    def display(self) -> dict:
        n = self.data
        return {
            "status": "success",
            "title": self.message,
            "detail": f"Driver: `{n.driver}` · Scope: `{n.scope}` · ID: `{n.id[:12]}`",
            "table": None,
        }


class RemoveNetworkResponse(BaseToolResponse):
    tool: str = "remove_network"
    data: dict  # {network: str}

    def display(self) -> dict:
        return {
            "status": "success",
            "title": self.message,
            "detail": f"Network: `{self.data['network']}`",
            "table": None,
        }


class ConnectNetworkResponse(BaseToolResponse):
    tool: str = "connect_container_to_network"
    data: dict  # {container: str, network: str}

    def display(self) -> dict:
        return {
            "status": "success",
            "title": self.message,
            "detail": f"Container `{self.data['container']}` → network `{self.data['network']}`",
            "table": None,
        }


class CreateDockerfileResponse(BaseToolResponse):
    tool: str = "create_dockerfile"

    def display(self) -> dict:
        return {"status": "success", "title": self.message, "detail": None, "table": None}


class CreateDockerignoreResponse(BaseToolResponse):
    tool: str = "create_dockerignore"

    def display(self) -> dict:
        return {"status": "success", "title": self.message, "detail": None, "table": None}


def tool_error(tool_name: str, message: str) -> str:
    return ErrorResponse(tool=tool_name, error=message).to_json()


_RESPONSE_REGISTRY: dict[str, type[BaseToolResponse]] = {
    "list_containers":             ListContainersResponse,
    "run_container":               RunContainerResponse,
    "stop_container":              StopContainerResponse,
    "remove_container":            RemoveContainerResponse,
    "restart_containers":          RestartContainersResponse,
    "get_docker_info":             DockerInfoResponse,
    "list_images":                 ListImagesResponse,
    "pull_image":                  PullImageResponse,
    "remove_image":                RemoveImageResponse,
    "build_image":                 BuildImageResponse,
    "list_networks":               ListNetworksResponse,
    "create_network":              CreateNetworkResponse,
    "remove_network":              RemoveNetworkResponse,
    "connect_container_to_network": ConnectNetworkResponse,
    "create_dockerfile":           CreateDockerfileResponse,
    "create_dockerignore":         CreateDockerignoreResponse,
    "error":                       ErrorResponse,
}


def parse_tool_response(raw: str) -> BaseToolResponse:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return ErrorResponse(tool="error", error=f"Invalid JSON: {raw[:200]}")

    # Error responses use status field, not tool name
    if data.get("status") == "error":
        return ErrorResponse.model_validate(data)

    tool_name = data.get("tool", "")
    cls = _RESPONSE_REGISTRY.get(tool_name, BaseToolResponse)
    return cls.model_validate(data)