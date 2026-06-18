import os
import json
import httpx
import mcp.types as types
from mcp.server import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Mount

port = int(os.environ.get("PORT", 8000))

POKEAPI_BASE = "https://pokeapi.co/api/v2"

server = Server("PokeAPI Bridge")

POKEMON_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "integer"},
        "name": {"type": "string"},
        "height_decimeters": {"type": "integer"},
        "weight_hectograms": {"type": "integer"},
        "types": {"type": "array", "items": {"type": "string"}},
        "stats": {"type": "object", "additionalProperties": {"type": "integer"}},
        "error": {"type": "string"},
    },
}

TYPE_SCHEMA = {
    "type": "object",
    "properties": {
        "type": {"type": "string"},
        "pokemon": {"type": "array", "items": {"type": "string"}},
        "error": {"type": "string"},
    },
}


@server.list_tools()
async def list_tools():
    return [
        types.Tool(
            name="get_pokemon",
            description="Busca dados de um Pokemon pelo nome (ex: 'pikachu'). Retorna id, altura, peso, tipos e status base.",
            inputSchema={
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
            outputSchema=POKEMON_SCHEMA,
        ),
        types.Tool(
            name="compare_pokemon",
            description="Compara o status base (stats) de dois Pokemon, lado a lado.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name1": {"type": "string"},
                    "name2": {"type": "string"},
                },
                "required": ["name1", "name2"],
            },
            outputSchema={
                "type": "object",
                "properties": {
                    "pokemon_1": POKEMON_SCHEMA,
                    "pokemon_2": POKEMON_SCHEMA,
                },
            },
        ),
        types.Tool(
            name="get_pokemon_by_type",
            description="Lista alguns Pokemon de um tipo especifico (ex: 'fire', 'water', 'electric').",
            inputSchema={
                "type": "object",
                "properties": {
                    "pokemon_type": {"type": "string"},
                    "limit": {"type": "integer", "default": 5},
                },
                "required": ["pokemon_type"],
            },
            outputSchema=TYPE_SCHEMA,
        ),
    ]


def _fetch_pokemon(name: str) -> dict:
    with httpx.Client(timeout=10) as client:
        resp = client.get(f"{POKEAPI_BASE}/pokemon/{name.lower().strip()}")
        if resp.status_code != 200:
            return {"error": f"Pokemon '{name}' not found"}
        data = resp.json()
        return {
            "id": data["id"],
            "name": data["name"],
            "height_decimeters": data["height"],
            "weight_hectograms": data["weight"],
            "types": [t["type"]["name"] for t in data["types"]],
            "stats": {s["stat"]["name"]: s["base_stat"] for s in data["stats"]},
        }


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "get_pokemon":
        result = _fetch_pokemon(arguments["name"])
    elif name == "compare_pokemon":
        result = {
            "pokemon_1": _fetch_pokemon(arguments["name1"]),
            "pokemon_2": _fetch_pokemon(arguments["name2"]),
        }
    elif name == "get_pokemon_by_type":
        pokemon_type = arguments["pokemon_type"]
        limit = arguments.get("limit", 5)
        with httpx.Client(timeout=10) as client:
            resp = client.get(f"{POKEAPI_BASE}/type/{pokemon_type.lower().strip()}")
            if resp.status_code != 200:
                result = {"error": f"Type '{pokemon_type}' not found"}
            else:
                data = resp.json()
                result = {
                    "type": pokemon_type,
                    "pokemon": [p["pokemon"]["name"] for p in data["pokemon"][:limit]],
                }
    else:
        result = {"error": f"Unknown tool: {name}"}

    return [types.TextContent(type="text", text=json.dumps(result))]


session_manager = StreamableHTTPSessionManager(
    app=server,
    event_store=None,
    json_response=False,
)

_mcp_starlette = Starlette(
    routes=[Mount("/mcp", app=session_manager.handle_request)],
    lifespan=session_manager.lifespan,
)
_mcp_starlette.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


async def app(scope, receive, send):
    if scope["type"] == "http" and scope["path"] == "/":
        response = JSONResponse({"status": "ok", "server": "PokeAPI MCP Bridge"})
        await response(scope, receive, send)
    else:
        await _mcp_starlette(scope, receive, send)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)
