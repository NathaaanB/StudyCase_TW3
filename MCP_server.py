#!/usr/bin/env python3
import asyncio
import base64
from pathlib import Path
from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from mcp.server.stdio import stdio_server
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# Création du serveur MCP
app = Server("serveur-web-automation")

# Une page globale pour la session (simplification pour démonstration)
browser = None
page = None

@app.list_tools()
async def list_tools() -> list[Tool]:
    """Liste tous les outils disponibles"""
    return [
        Tool(
            name="naviguer_web",
            description="Navigue vers une URL spécifiée avec gestion des erreurs et timeout",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL à visiter"},
                    "timeout": {"type": "number", "description": "Timeout en secondes (optionnel, défaut 10s)"}
                },
                "required": ["url"]
            }
        ),
        Tool(
            name="capture_ecran",
            description="Prend une capture d'écran de la page courante",
            inputSchema={
                "type": "object",
                "properties": {
                    "full_page": {"type": "boolean", "description": "Capturer la page entière", "default": False}
                }
            }
        ),
        Tool(
            name="extraire_liens",
            description="Extrait tous les liens de la page courante, avec option de filtrage par texte",
            inputSchema={
                "type": "object",
                "properties": {
                    "filtre": {"type": "string", "description": "Filtrer les liens contenant ce texte (optionnel)"}
                }
            }
        ),
        Tool(
            name="remplir_champ",
            description="Remplit un champ identifié par un sélecteur CSS",
            inputSchema={
                "type": "object",
                "properties": {
                    "selecteur": {"type": "string", "description": "Sélecteur CSS de l'élément"},
                    "valeur": {"type": "string", "description": "Valeur à remplir"}
                },
                "required": ["selecteur", "valeur"]
            }
        ),
        Tool(
            name="clic_element",
            description="Clique sur un élément identifié par un sélecteur CSS",
            inputSchema={
                "type": "object",
                "properties": {
                    "selecteur": {"type": "string", "description": "Sélecteur CSS de l'élément à cliquer"}
                },
                "required": ["selecteur"]
            }
        ),
        Tool(
            name="recuperer_html",
            description="Récupère le code HTML complet de la page courante",
            inputSchema={"type": "object"}
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    global browser, page

    if browser is None:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()

    try:
        if name == "naviguer_web":
            url = arguments["url"]
            timeout_val = arguments.get("timeout", 10)
            try:
                await page.goto(url, timeout=timeout_val * 1000)
                return [TextContent(type="text", text=f"Navigation réussie vers {url}")]
            except PlaywrightTimeoutError:
                return [TextContent(type="text", text=f"Timeout lors de la navigation vers {url}")]
            except Exception as e:
                return [TextContent(type="text", text=f"Erreur lors de la navigation vers {url}: {str(e)}")]

        elif name == "capture_ecran":
            full_page = arguments.get("full_page", False)
            project_dir = Path(__file__).parent
            filename = f"screenshot_{int(asyncio.get_event_loop().time())}.png"
            path = f"{project_dir}/screenshots/{filename}"
            await page.screenshot(path=path, full_page=full_page)
            
            with open(path, "rb") as f:
                img_data = f.read()
                img_base64 = base64.b64encode(img_data).decode("utf-8")
            
            return [
                TextContent(type="text", text=f"Capture d'écran sauvegardée: {path}"),
                ImageContent(
                    type="image",
                    data=img_base64,
                    mimeType="image/png"
                )
            ]

        elif name == "extraire_liens":
            filtre = arguments.get("filtre", None)
            liens = await page.eval_on_selector_all("a", "els => els.map(e => ({text: e.innerText, href: e.href}))")
            if filtre:
                liens = [l for l in liens if filtre.lower() in l["text"].lower()]
            if not liens:
                return [TextContent(type="text", text="Aucun lien trouvé avec ce filtre.")]
            return [TextContent(type="text", text="\n".join([f"{l['text']} -> {l['href']}" for l in liens[:20]]))]

        elif name == "remplir_champ":
            selecteur = arguments["selecteur"]
            valeur = arguments["valeur"]
            try:
                await page.fill(selecteur, valeur)
                return [TextContent(type="text", text=f"Champ {selecteur} rempli avec '{valeur}'")]
            except Exception as e:
                return [TextContent(type="text", text=f"Impossible de remplir le champ {selecteur}: {str(e)}")]

        elif name == "clic_element":
            selecteur = arguments["selecteur"]
            try:
                await page.click(selecteur)
                return [TextContent(type="text", text=f"Clic effectué sur {selecteur}")]
            except Exception as e:
                return [TextContent(type="text", text=f"Impossible de cliquer sur {selecteur}: {str(e)}")]

        elif name == "recuperer_html":
            html = await page.content()
            return [TextContent(type="text", text=html[:2000] + ("..." if len(html) > 2000 else ""))]

        else:
            return [TextContent(type="text", text=f"Outil inconnu: {name}")]

    except Exception as e:
        return [TextContent(type="text", text=f"Erreur inattendue: {str(e)}")]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())