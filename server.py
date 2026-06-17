from mcp.server.fastmcp import FastMCP
import httpx

mcp = FastMCP("Pokemon MCP Bridge")

POKEAPI = "https://pokeapi.co/api/v2"


@mcp.tool()
def get_pokemon(name: str):
    r = httpx.get(f"{POKEAPI}/pokemon/{name}", timeout=10)
    if r.status_code != 200:
        return {"error": "not found"}
    return r.json()


@mcp.tool()
def compare_pokemon(name1: str, name2: str):
    return {
        "pokemon_1": get_pokemon(name1),
        "pokemon_2": get_pokemon(name2)
    }


@mcp.tool()
def get_pokemon_by_type(pokemon_type: str):
    r = httpx.get(f"{POKEAPI}/type/{pokemon_type}", timeout=10)
    if r.status_code != 200:
        return {"error": "not found"}

    data = r.json()
    return {
        "type": pokemon_type,
        "pokemon": [p["pokemon"]["name"] for p in data["pokemon"][:10]]
    }


# IMPORTANTÍSSIMO: só expõe o ASGI app
app = mcp.streamable_http_app()