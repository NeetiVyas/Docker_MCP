import asyncio
import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from config.settings import SERVER_NAME, SERVER_VERSION
from schemas.tool_schemas import *
from tools.docker_tools import *
from tools.file_tools import create_dockerfile

app = Server(SERVER_NAME)

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="list_containers",
            description="List all currently running Docker containers. Returns id, name, image, and status for each.",
            inputSchema=ListContainersInput.model_json_schema()
        ),
        Tool (
            name="run_container",
            description="Run a Docker container from an image. The image will be pulled automatically if not available locally.",
            inputSchema=RunContainerInput.model_json_schema()
        ),
        Tool(
            name="stop_container",
            description="Scan a project folder and generate a customized Dockerfile. Auto-detects language, framework, and entry point.",
            inputSchema=StopContainerInput.model_json_schema()
        ),
        Tool(
            name="create_dockerfile",
            description="Generate a starter Dockerfile for a given language (python, node, or go) and save it to disk.",
            inputSchema=CreateDockerfileInput.model_json_schema()
        ),
        Tool(
            name="restart_container",
            description = "Restart one or more containers by name or ID.",
            inputSchema = RestartContainersInput.model_json_schema()
        ),
        Tool(
            name="get_docker_info",
            description="Get Docker engine info: version, OS, total containers and images.",
            inputSchema=GetDockerInfoInput.model_json_schema()
        ),
        Tool(
            name="list_images",
            description="list all locally available docker images with size and tags",
            inputSchema=ListImagesInput.model_json_schema()
        ),
        Tool(
            name="pull_image",
            description="Pull a Docker image from Docker Hub without running it.",
            inputSchema=PullImageInput.model_json_schema()
        ),
        Tool(
            name="remove_image",
            description="Remove a local Docker image by name or ID.",
            inputSchema=RemoveImageInput.model_json_schema()
        ),
        Tool(
            name="build_image",
            description="Build a Docker image from a Dockerfile in the given folder path.",
            inputSchema=BuildImageInput.model_json_schema()
        ),
        Tool(
            name="list_networks",
            description="List all Docker networks.",
            inputSchema=ListNetworksInput.model_json_schema()
        ),
        Tool(
            name="create_network",
            description="Create a new Docker network.",
            inputSchema=CreateNetworkInput.model_json_schema()
        ),
        Tool(
            name="connect_container_to_network",
            description="Connect a running container to a Docker network.",
            inputSchema=ConnectContainerToNetworkInput.model_json_schema()
        ),
        Tool(
            name="remove_container",
            description="Permanently remove a stopped container. Use force=true to remove running containers.",
            inputSchema=RemoveContainerInput.model_json_schema()
        ),
        Tool(
            name="remove_network",
            description="Remove a Docker network by name or ID.",
            inputSchema=RemoveNetworkInput.model_json_schema()
        ),
        Tool(
            name="create_dockerignore",
            description="build a dockerignore file to ignore the files not required for setting up project like .git, venv, .env",
            inputSchema=CreateDockerIgnoreFileInput.model_json_schema()
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "list_containers":
        result = list_containers(show_all=arguments.get("show_all", False))

    elif name=="run_container":
        result = run_container(
            image=arguments["image"],                         
            name=arguments.get("name"),                       
            detach=arguments.get("detach"),                    
        )

    elif name=="stop_container":
        result = stop_container(
            container_id=arguments["container_id"]
        )

    elif name == "create_dockerfile":
        result = create_dockerfile(
            project_path=arguments["project_path"],           
            language=arguments.get("language"),              
            output_path=arguments.get("output_path"),        
        )

    elif name == "restart_container":
        result = restart_container(container_ids=arguments["container_ids"])

    elif name == "get_docker_info":
        result = get_docker_info()

    elif name == "list_images":
        result = list_images()
    
    elif name == "pull_image":
        result = pull_image(image=arguments["image"])

    elif name == "remove_image":
        result = remove_image(
            image=arguments["image"],
            force=arguments.get("force", False),
        )
    
    elif name == "build_image":
        result = build_image(
            path=arguments["path"],
            tag=arguments["tag"],
        )
 
    elif name == "list_networks":
        result = list_networks()
 
    elif name == "create_network":
        result = create_network(
            name=arguments["name"],
            driver=arguments.get("driver", "bridge"),
        )
 
    elif name == "remove_network":
        result = remove_network(network_name=arguments["network_name"])
 
    elif name == "connect_container_to_network":
        result = connect_container_to_network(
            container_id=arguments["container_id"],
            network_name=arguments["network_name"],
        )
        
    elif name == "remove_container":
        result = remove_container(
            container_id=arguments["container_id"],
            force=arguments.get("force", False),
        )

    else:
        result = json.dumps({"status": "error", "message": f"Unknown tool: '{name}'"})

    return [TextContent(type="text", text=result)]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )
 
 
if __name__ == "__main__":
    asyncio.run(main())