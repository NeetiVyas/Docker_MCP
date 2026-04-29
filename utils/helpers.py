import json


def success(data: str | list | dict):
    return json.dumps({"status": "success", "data": data}, indent=2)


def error(message: str):
    return json.dumps({"status": "error", "message": message}, indent=2)


def format_container(container) -> dict:
    return {
        "id":     container.id,          
        "name":   container.name,              
        "image":  container.image.tags[0] if container.image.tags else "unknown",
        "status": container.status,            
    }