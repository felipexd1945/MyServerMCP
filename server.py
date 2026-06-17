import os
import httpx
from mcp.server.fastmcp import FastMCP
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

port = int(os.environ.get("PORT", 8000))
mcp = FastMCP("PokeAPI Bridge", host="0.0.0.0", port=port)

POKEAPI_BASE = "https://pokeapi.co/api/v2"


class PokemonOutput(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    height_decimeters: Optional[int] = None
    weight_hectograms: Optional[int] = None
    types: Optional[list[str]] = None
    stats: Optional[dict[str, int]] = None
    error: Optional[str] = None


class CompareOutput(BaseModel):
    pokemon_1: PokemonOutput
    pokemon_2: PokemonOutput


class TypeOutput(BaseModel):
    type: Optional[str] = None
    pokemon: Optional[list[str]] = None
    error: Optional[str] = None


def _fetch_pokemon(name: str) -> PokemonOutput:
    with httpx.Client(timeout=10) as client:
        resp = client.get(f"{POKEAPI_BASE}/pokemon/{name.lower().strip()}")
        if resp.status_code != 200:
            return PokemonOutput(error=f"Pokemon '{name}' not found")
        data = resp.json()
        return PokemonOutput(
            id=data["id"],
            name=data["name"],
            height_decimeters=data["height"],
            weight_hectograms=data["weight"],
            types=[t["type"]["name"] for t in data["types"]],
            stats={s["stat"]["name"]: s["base_stat"] for s in data["stats"]},
        )


@mcp.tool()
def get_pokemon(name: str) -> PokemonOutput:
    """Busca dados de um Pokemon pelo nome (ex: 'pikachu'). Retorna id, altura, peso, tipos e status base."""
    return _fetch_pokemon(name)


@mcp.tool()
def compare_pokemon(name1: str, name2: str) -> CompareOutput:
    """Compara o status base (stats) de dois Pokemon, lado a lado."""
    return CompareOutput(
        pokemon_1=_fetch_pokemon(name1),
        pokemon_2=_fetch_pokemon(name2),
    )


@mcp.tool()
def get_pokemon_by_type(pokemon_type: str, limit: int = 5) -> TypeOutput:
    """Lista alguns Pokemon de um tipo especifico (ex: 'fire', 'water', 'electric')."""
    with httpx.Client(timeout=10) as client:
        resp = client.get(f"{POKEAPI_BASE}/type/{pokemon_type.lower().strip()}")
        if resp.status_code != 200:
            return TypeOutput(error=f"Type '{pokemon_type}' not found")
        data = resp.json()
        return TypeOutput(
            type=pokemon_type,
            pokemon=[p["pokemon"]["name"] for p in data["pokemon"][:limit]],
        )


_mcp_asgi = mcp.streamable_http_app()
_mcp_asgi.add_middleware(
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
        await _mcp_asgi(scope, receive, send)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)
