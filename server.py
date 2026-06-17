from mcp.server.fastmcp import FastMCP
import httpx

mcp = FastMCP("Pokemon MCP Bridge")

POKEAPI = "https://pokeapi.co/api/v2"


@mcp.tool()
def get_pokemon(name: str) -> dict:
    """Get basic Pokemon data"""

    r = httpx.get(
        f"{POKEAPI}/pokemon/{name.lower().strip()}",
        timeout=10
    )

    if r.status_code != 200:
        return {"error": "pokemon not found"}

    data = r.json()

    return {
        "id": data["id"],
        "name": data["name"],
        "types": [
            t["type"]["name"]
            for t in data["types"]
        ],
        "height": data["height"],
        "weight": data["weight"]
    }


@mcp.tool()
def compare_pokemon(name1: str, name2: str) -> dict:
    """Compare two Pokémon"""

    return {
        "pokemon_1": get_pokemon(name1),
        "pokemon_2": get_pokemon(name2)
    }


@mcp.tool()
def get_pokemon_by_type(pokemon_type: str) -> dict:
    """Get Pokémon by type"""

    r = httpx.get(
        f"{POKEAPI}/type/{pokemon_type.lower().strip()}",
        timeout=10
    )

    if r.status_code != 200:
        return {"error": "type not found"}

    data = r.json()

    return {
        "type": pokemon_type,
        "pokemon": [
            p["pokemon"]["name"]
            for p in data["pokemon"][:10]
        ]
    }


# ✅ CRÍTICO: export correto para Streamable HTTP (Agentforce MCP)
app = mcp.streamable_http_app()