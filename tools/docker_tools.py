# import os
# import docker
# import docker.errors
# from schemas.response_schema import *
# from config.settings import STOP_TIMEOUT, DEFAULT_DETACH
# from utils.helpers import success, error, format_container


# def get_docker_client():
#     return docker.from_env()


# def _container_info(container) -> ContainerInfo:
#     return ContainerInfo(
#         id=container.id,
#         name=container.name,
#         image=container.image.tags[0] if container.image.tags else "unknown",
#         status=container.status,
#     ) 
 

# def _image_info(img) -> ImageInfo:
#     return ImageInfo(
#         id=img.id,
#         tags=img.tags if img.tags else ["<untagged>"],
#         size_mb=round(img.attrs.get("Size", 0) / 1024 / 1024, 2),
#         created=img.attrs.get("Created", "")[:10],
#     )


# def _resolve_container(client, identifier: str):
#     try:
#         return client.containers.get(identifier)
#     except docker.errors.NotFound:
#         matches = [
#             c for c in client.containers.list(all=True)
#             if c.name == identifier or c.id.startswith(identifier)
#         ]
#         if len(matches) == 1:
#             return matches[0]
#         elif len(matches) > 1:
#             names = ", ".join(c.name for c in matches)
#             raise ValueError(f"Ambiguous identifier '{identifier}' matches multiple containers: {names}. Please be more specific.")
#         raise docker.errors.NotFound(f"No container found with name or ID: '{identifier}'")


# def list_containers(show_all: bool = False) -> str:
#     try:
#         client = get_docker_client()
#         containers = client.containers.list(all=show_all)
#         print("list containers returns\n", len(containers))
#         return ListContainersResponse(
#             total=len(containers),
#             filter="all" if show_all else "running",
#             containers=[_container_info(c) for c in containers],
#         ).to_json()
    
#     except docker.errors.DockerException as e:
#         return error(f"Could not connect to Docker: {str(e)}")
    

# def run_container(image: str, name: str = None, detach: bool = True) -> str:
#     try:
#         client = get_docker_client()
#         run_kwargs = {
#             "image":  image,
#             "detach": True,  
#         }
#         if name:
#             run_kwargs["name"] = name

#         container = client.containers.run(**run_kwargs)

#         import time
#         time.sleep(2)
#         container.reload()   

#         return RunContainerResponse(
#             message=f"Container started from image '{image}'",
#             container=_container_info(container),
#         ).to_json()

#     except docker.errors.ImageNotFound:
#         return tool_error("run_container", f"Image '{image}' not found locally. Pull it first.")
#     except docker.errors.APIError as e:
#         return tool_error("run_container", f"Docker API error: {str(e)}")
    

# def stop_container(container_id: str) -> str:
#     try:
#         client    = get_docker_client()
#         container = _resolve_container(client, container_id)
#         container.stop(timeout=STOP_TIMEOUT)
#         return StopContainerResponse(
#             message=f"Container '{container_id}' stopped successfully.",
#             container_id=container_id,
#         ).to_json()
#     except ValueError as e:
#         return tool_error("stop_container", str(e))
#     except docker.errors.NotFound:
#         return tool_error("stop_container", f"No container found with name or ID: '{container_id}'.")
#     except docker.errors.APIError as e:
#         return tool_error("stop_container", f"Docker API error: {str(e)}")
    

# def restart_container(container_ids: list[str]) -> str:
#     try:
#         client  = get_docker_client()
#         results = []
#         for identifier in container_ids:
#             try:
#                 container = _resolve_container(client, identifier)
#                 container.restart()
#                 results.append(RestartResult(container=identifier, status="restarted"))
#             except ValueError as e:
#                 results.append(RestartResult(container=identifier, status="error", reason=str(e)))
#             except docker.errors.NotFound:
#                 results.append(RestartResult(container=identifier, status="error", reason=f"No container found with name or ID: '{identifier}'"))
#             except docker.errors.APIError as e:
#                 results.append(RestartResult(container=identifier, status="error", reason=str(e)))
 
#         all_ok = all(r.status == "restarted" for r in results)
#         return RestartContainersResponse(
#             message="All containers restarted." if all_ok else "Some containers failed.",
#             results=results,
#         ).to_json()
#     except docker.errors.DockerException as e:
#         return tool_error("restart_containers", f"Could not connect to Docker: {str(e)}")
    
        
# def get_docker_info() -> str:
#     try:
#         client  = get_docker_client()
#         info    = client.info()
#         version = client.version()
#         return DockerInfoResponse(
#             docker_version=version.get("Version", "unknown"),
#             os=info.get("OperatingSystem", "unknown"),
#             architecture=info.get("Architecture", "unknown"),
#             total_containers=info.get("Containers", 0),
#             running=info.get("ContainersRunning", 0),
#             stopped=info.get("ContainersStopped", 0),
#             total_images=info.get("Images", 0),
#             memory_limit=info.get("MemTotal", 0),
#         ).to_json()
#     except docker.errors.DockerException as e:
#         return tool_error("get_docker_info", f"Could not connect to Docker: {str(e)}")
    

# def list_images() -> str:
#     try:
#         client = get_docker_client()
#         images = client.images.list()
#         return ListImagesResponse(
#             total=len(images),
#             images=[_image_info(img) for img in images],
#         ).to_json()
#     except docker.errors.DockerException as e:
#         return tool_error("list_images", f"Could not connect to Docker: {str(e)}")
    

# def pull_image(image: str) -> str:
#     try:
#         client = get_docker_client()
#         pulled = client.images.pull(image)
#         return PullImageResponse(
#             message=f"Image '{image}' pulled successfully.",
#             image=_image_info(pulled),
#         ).to_json()
#     except docker.errors.ImageNotFound:
#         return tool_error("pull_image", f"Image '{image}' not found on Docker Hub.")
#     except docker.errors.APIError as e:
#         return tool_error("pull_image", f"Docker API error: {str(e)}")
    

# def remove_image(image: str, force: bool = False) -> str:
#     try:
#         client = get_docker_client()
#         # img_obj = client.images.get(image)  # <-- add this
#         # print(f"Resolved '{image}' → ID: {img_obj.id}, Tags: {img_obj.tags}")
#         client.images.remove(image=image, force=force)
#         return RemoveImageResponse(
#             message=f"Image '{image}' removed successfully.",
#             image=image,
#             forced=force,
#         ).to_json()
    
#     except docker.errors.ImageNotFound:
#         return tool_error("remove_image", f"Image '{image}' not found locally.")
#     except docker.errors.APIError as e:
#         return tool_error("remove_image", f"Docker API error: {str(e)}")
    

# def remove_container(container_id: str, force: bool = False) -> str:
#     try:
#         client  = get_docker_client()
#         container = _resolve_container(client, container_id)
#         actual_id = container.id
#         container.remove(force=force)
#         return RemoveContainerResponse(
#             message=f"Container '{container_id}' removed successfully.",
#             container_id=actual_id,
#             forced=force,
#         ).to_json()
    
#     except ValueError as e:
#         return tool_error("remove_container", str(e))
#     except docker.errors.NotFound:
#         return tool_error("remove_container", f"No container found with name or ID: '{container_id}'.")
#     except docker.errors.APIError as e:
#         return tool_error("remove_container", f"Docker API error: {str(e)}")


# def build_image(path: str, tag: str) -> str:
#     try:
#         if not os.path.exists(path):
#             return tool_error("build_image", f"Path '{path}' does not exist.")
#         if not os.path.exists(os.path.join(path, "Dockerfile")):
#             return tool_error("build_image", f"No Dockerfile found in '{path}'.")
 
#         client = get_docker_client()
#         image, log_stream = client.images.build(path=path, tag=tag, rm=True)
#         log_lines        = [
#             chunk.get("stream", "").strip()
#             for chunk in log_stream
#             if chunk.get("stream", "").strip()
#         ]
#         return BuildImageResponse(
#             message=f"Image '{tag}' built successfully.",
#             id=image.id,
#             tag=tag,
#             build_logs=log_lines[-10:],
#         ).to_json()
    
#     except docker.errors.BuildError as e:
#         return tool_error("build_image", f"Build failed: {str(e)}")
#     except docker.errors.APIError as e:
#         msg = str(e)
#         if "input/output error" in msg or "blob" in msg and "expected at" in msg:
#             return tool_error(
#                 "build_image",
#                 "Docker storage is corrupted (input/output error on a blob). "
#                 "Fix: run 'docker system prune -a --volumes' to clean the store, "
#                 "then retry. If the error persists, reset Docker Desktop to factory defaults."
#             )
#         return tool_error("build_image", f"Docker API error: {str(e)}")
    

# def list_networks() -> str:
#     try:
#         client   = get_docker_client()
#         networks = client.networks.list()
#         return ListNetworksResponse(
#             total=len(networks),
#             networks=[
#                 NetworkInfo(
#                     id=net.id,
#                     name=net.name,
#                     driver=net.attrs.get("Driver", "unknown"),
#                     scope=net.attrs.get("Scope", "unknown"),
#                 )
#                 for net in networks
#             ],
#         ).to_json()
#     except docker.errors.DockerException as e:
#         return tool_error("list_networks", f"Could not connect to Docker: {str(e)}")
    

# def create_network(name: str, driver: str = "bridge") -> str:
#     try:
#         client  = get_docker_client()
#         network = client.networks.create(name=name, driver=driver)
#         return CreateNetworkResponse(
#             message=f"Network '{name}' created successfully.",
#             network=NetworkInfo(
#                 id=network.id,
#                 name=name,
#                 driver=driver,
#                 scope="local",
#             ),
#         ).to_json()
#     except docker.errors.APIError as e:
#         return tool_error("create_network", f"Docker API error: {str(e)}")
    

# def remove_network(network_name: str) -> str:
#     try:
#         client  = get_docker_client()
#         network = client.networks.get(network_name)
#         network.remove()
#         return RemoveNetworkResponse(
#             message=f"Network '{network_name}' removed successfully.",
#             network=network_name,
#         ).to_json()
#     except docker.errors.NotFound:
#         return tool_error("remove_network", f"Network '{network_name}' not found.")
#     except docker.errors.APIError as e:
#         return tool_error("remove_network", f"Docker API error: {str(e)}")
    

# def connect_container_to_network(container_id: str, network_name: str) -> str:
#     try:
#         client    = get_docker_client()
#         network   = client.networks.get(network_name)
#         container = _resolve_container(client, container_id)
#         network.connect(container)
#         return ConnectNetworkResponse(
#             message=f"Container '{container_id}' connected to network '{network_name}'.",
#             container=container_id,
#             network=network_name,
#         ).to_json()
#     except ValueError as e:
#         return tool_error("connect_container_to_network", str(e))
#     except docker.errors.NotFound as e:
#         return tool_error("connect_container_to_network", f"Not found: {str(e)}")
#     except docker.errors.APIError as e:
#         return tool_error("connect_container_to_network", f"Docker API error: {str(e)}")



import os
import docker
import docker.errors
from schemas.response_schema import *
from config.settings import STOP_TIMEOUT


def get_docker_client():
    return docker.from_env()


def _container_info(container) -> ContainerInfo:
    return ContainerInfo(
        id=container.id,
        name=container.name,
        image=container.image.tags[0] if container.image.tags else "unknown",
        status=container.status,
    )


def _image_info(img) -> ImageInfo:
    return ImageInfo(
        id=img.id,
        tags=img.tags if img.tags else ["<untagged>"],
        size_mb=round(img.attrs.get("Size", 0) / 1024 / 1024, 2),
        created=img.attrs.get("Created", "")[:10],
    )


def _resolve_container(client, identifier: str):
    try:
        return client.containers.get(identifier)
    except docker.errors.NotFound:
        matches = [
            c for c in client.containers.list(all=True)
            if c.name == identifier or c.id.startswith(identifier)
        ]
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            names = ", ".join(c.name for c in matches)
            raise ValueError(f"Ambiguous identifier '{identifier}' matches: {names}")
        raise docker.errors.NotFound(f"No container found: '{identifier}'")


def list_containers(show_all: bool = False) -> str:
    try:
        client = get_docker_client()
        containers = client.containers.list(all=show_all)
        return ListContainersResponse(
            filter="all" if show_all else "running",
            data=[_container_info(c) for c in containers],
        ).to_json()
    except docker.errors.DockerException as e:
        return tool_error("list_containers", f"Could not connect to Docker: {str(e)}")


def run_container(image: str, name: str = None, detach: bool = True) -> str:
    try:
        client = get_docker_client()
        run_kwargs = {"image": image, "detach": True}
        if name:
            run_kwargs["name"] = name
        container = client.containers.run(**run_kwargs)

        import time
        time.sleep(2)
        container.reload()

        return RunContainerResponse(
            message=f"Container started from image '{image}'",
            data=_container_info(container),
        ).to_json()
    except docker.errors.ImageNotFound:
        return tool_error("run_container", f"Image '{image}' not found locally. Pull it first.")
    except docker.errors.APIError as e:
        return tool_error("run_container", f"Docker API error: {str(e)}")


def stop_container(container_id: str) -> str:
    try:
        client = get_docker_client()
        container = _resolve_container(client, container_id)
        container.stop(timeout=STOP_TIMEOUT)
        container.reload()
        return StopContainerResponse(
            message=f"Container '{container.name}' stopped successfully.",
            data=_container_info(container),
        ).to_json()
    except ValueError as e:
        return tool_error("stop_container", str(e))
    except docker.errors.NotFound:
        return tool_error("stop_container", f"No container found: '{container_id}'.")
    except docker.errors.APIError as e:
        return tool_error("stop_container", f"Docker API error: {str(e)}")


def restart_container(container_ids: list[str]) -> str:
    try:
        client = get_docker_client()
        results = []
        for identifier in container_ids:
            try:
                container = _resolve_container(client, identifier)
                container.restart()
                results.append(RestartResult(container=identifier, status="restarted"))
            except ValueError as e:
                results.append(RestartResult(container=identifier, status="error", reason=str(e)))
            except docker.errors.NotFound:
                results.append(RestartResult(container=identifier, status="error", reason=f"Not found: '{identifier}'"))
            except docker.errors.APIError as e:
                results.append(RestartResult(container=identifier, status="error", reason=str(e)))

        all_ok = all(r.status == "restarted" for r in results)
        return RestartContainersResponse(
            message="All containers restarted." if all_ok else "Some containers failed.",
            data=results,
        ).to_json()
    except docker.errors.DockerException as e:
        return tool_error("restart_containers", f"Could not connect to Docker: {str(e)}")


def get_docker_info() -> str:
    try:
        client = get_docker_client()
        info = client.info()
        version = client.version()
        return DockerInfoResponse(
            message="Docker daemon info",
            data={
                "version":      version.get("Version", "unknown"),
                "os":           info.get("OperatingSystem", "unknown"),
                "architecture": info.get("Architecture", "unknown"),
                "containers":   info.get("Containers", 0),
                "running":      info.get("ContainersRunning", 0),
                "stopped":      info.get("ContainersStopped", 0),
                "images":       info.get("Images", 0),
                "memory_gb":    round(info.get("MemTotal", 0) / 1024 / 1024 / 1024, 1),
            },
        ).to_json()
    except docker.errors.DockerException as e:
        return tool_error("get_docker_info", f"Could not connect to Docker: {str(e)}")


def list_images() -> str:
    try:
        client = get_docker_client()
        images = client.images.list()
        return ListImagesResponse(
            data=[_image_info(img) for img in images],
        ).to_json()
    except docker.errors.DockerException as e:
        return tool_error("list_images", f"Could not connect to Docker: {str(e)}")


def pull_image(image: str) -> str:
    try:
        client = get_docker_client()
        pulled = client.images.pull(image)
        return PullImageResponse(
            message=f"Image '{image}' pulled successfully.",
            data=_image_info(pulled),
        ).to_json()
    except docker.errors.ImageNotFound:
        return tool_error("pull_image", f"Image '{image}' not found on Docker Hub.")
    except docker.errors.APIError as e:
        return tool_error("pull_image", f"Docker API error: {str(e)}")


def remove_image(image: str, force: bool = False) -> str:
    try:
        client = get_docker_client()
        client.images.remove(image=image, force=force)
        return RemoveImageResponse(
            message=f"Image '{image}' removed successfully.",
            data={"image": image, "forced": force},
        ).to_json()
    except docker.errors.ImageNotFound:
        return tool_error("remove_image", f"Image '{image}' not found locally.")
    except docker.errors.APIError as e:
        return tool_error("remove_image", f"Docker API error: {str(e)}")


def remove_container(container_id: str, force: bool = False) -> str:
    try:
        client = get_docker_client()
        container = _resolve_container(client, container_id)
        info = _container_info(container)   # capture before removal
        container.remove(force=force)
        return RemoveContainerResponse(
            message=f"Container '{info.name}' removed successfully.",
            data=info,
            forced=force,
        ).to_json()
    except ValueError as e:
        return tool_error("remove_container", str(e))
    except docker.errors.NotFound:
        return tool_error("remove_container", f"No container found: '{container_id}'.")
    except docker.errors.APIError as e:
        return tool_error("remove_container", f"Docker API error: {str(e)}")


def build_image(path: str, tag: str) -> str:
    try:
        if not os.path.exists(path):
            return tool_error("build_image", f"Path '{path}' does not exist.")
        if not os.path.exists(os.path.join(path, "Dockerfile")):
            return tool_error("build_image", f"No Dockerfile found in '{path}'.")

        client = get_docker_client()
        image, log_stream = client.images.build(path=path, tag=tag, rm=True)
        log_lines = [
            chunk.get("stream", "").strip()
            for chunk in log_stream
            if chunk.get("stream", "").strip()
        ]
        return BuildImageResponse(
            message=f"Image '{tag}' built successfully.",
            data={"id": image.id, "tag": tag, "build_logs": log_lines[-10:]},
        ).to_json()
    except docker.errors.BuildError as e:
        return tool_error("build_image", f"Build failed: {str(e)}")
    except docker.errors.APIError as e:
        msg = str(e)
        if "input/output error" in msg or ("blob" in msg and "expected at" in msg):
            return tool_error("build_image", "Docker storage is corrupted. Run 'docker system prune -a --volumes' and retry.")
        return tool_error("build_image", f"Docker API error: {str(e)}")


def list_networks() -> str:
    try:
        client = get_docker_client()
        networks = client.networks.list()
        return ListNetworksResponse(
            data=[
                NetworkInfo(
                    id=net.id,
                    name=net.name,
                    driver=net.attrs.get("Driver", "unknown"),
                    scope=net.attrs.get("Scope", "unknown"),
                )
                for net in networks
            ],
        ).to_json()
    except docker.errors.DockerException as e:
        return tool_error("list_networks", f"Could not connect to Docker: {str(e)}")


def create_network(name: str, driver: str = "bridge") -> str:
    try:
        client = get_docker_client()
        network = client.networks.create(name=name, driver=driver)
        return CreateNetworkResponse(
            message=f"Network '{name}' created successfully.",
            data=NetworkInfo(id=network.id, name=name, driver=driver, scope="local"),
        ).to_json()
    except docker.errors.APIError as e:
        return tool_error("create_network", f"Docker API error: {str(e)}")


def remove_network(network_name: str) -> str:
    try:
        client = get_docker_client()
        network = client.networks.get(network_name)
        network.remove()
        return RemoveNetworkResponse(
            message=f"Network '{network_name}' removed successfully.",
            data={"network": network_name},
        ).to_json()
    except docker.errors.NotFound:
        return tool_error("remove_network", f"Network '{network_name}' not found.")
    except docker.errors.APIError as e:
        return tool_error("remove_network", f"Docker API error: {str(e)}")


def connect_container_to_network(container_id: str, network_name: str) -> str:
    try:
        client = get_docker_client()
        network = client.networks.get(network_name)
        container = _resolve_container(client, container_id)
        network.connect(container)
        return ConnectNetworkResponse(
            message=f"Container '{container_id}' connected to network '{network_name}'.",
            data={"container": container_id, "network": network_name},
        ).to_json()
    except ValueError as e:
        return tool_error("connect_container_to_network", str(e))
    except docker.errors.NotFound as e:
        return tool_error("connect_container_to_network", f"Not found: {str(e)}")
    except docker.errors.APIError as e:
        return tool_error("connect_container_to_network", f"Docker API error: {str(e)}")