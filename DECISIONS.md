# Décisions Techniques - Serveur MCP

Documentation des choix architecturaux et techniques du serveur MCP de web scraping.

---

## 1. Architecture Globale du Serveur

### 1.1 Protocole MCP (Model Context Protocol)

**Choix :** Implémentation d'un serveur MCP pour exposer les outils de web automation

**Justification :**
- **Standardisation** : Protocole MCP d'Anthropic = interface standardisée pour agents IA
- **Découverte dynamique** : Les clients peuvent interroger `list_tools()` pour découvrir les capacités
- **Communication JSON-RPC via stdio** : Pas de gestion réseau, sécurité renforcée, latence minimale
- **Typage strict** : Schémas d'outils avec validation via Pydantic

**Alternative rejetée :** API REST HTTP
- Plus complexe (gestion ports, authentification, CORS)
- Latence supérieure pour communication locale
- Non standard pour intégration LLM

### 1.2 Structure

```
mcp_server/
├── server.py              # Point d'entrée, orchestration MCP
├── tools_definitions.py   # Schémas des outils (contrat)
├── tool_dispatcher.py     # Routage des appels
├── web_tools.py          # Implémentations Playwright
└── scraping_tools.py     # Extraction de données LLM-assistée
```

**Justification :**
- **Séparation claire** : Contrat (definitions) ↔ Dispatch (routing) ↔ Implémentation (tools)
- **Maintenabilité** : Ajout d'un outil = 1 ligne dans definitions, 1 fonction dans web_tools/scraping_tools
- **Testabilité** : Chaque module testable indépendamment
- **Réutilisabilité** : `web_tools.py` réutilisable dans d'autres contextes

---

## 2. Choix Techniques

### 2.1 Langage : Python 3.9+ avec Asyncio

**Justification :**
- **MCP natif** : Bibliothèque officielle `mcp>=0.9.0` en Python
- **Asyncio** : Gestion asynchrone native (essentielle pour Playwright et I/O stdio)
- **Écosystème** : BeautifulSoup, LiteLLM, Playwright tous optimisés pour Python

### 2.2 Bibliothèque d'Automation : Playwright

**Choix :** `playwright>=1.40.0`

**Justification :**
- **Rendu JavaScript** : Supporte SPA modernes (React, Vue, Angular)
- **API asynchrone** : S'intègre parfaitement avec `asyncio`
- **Multi-navigateurs** : Chromium, Firefox, WebKit (choix Chromium pour compatibilité)
- **Gestion d'erreurs** : Timeouts configurables, exceptions claires

**Alternative rejetée :** Selenium
- API synchrone (bloquante)
- Performances inférieures sur sites modernes
- Setup plus complexe (drivers séparés)

### 2.3 Parsing HTML : BeautifulSoup4

**Justification :**
- Complémentaire à Playwright pour analyse DOM
- Utilisé dans `scraping_tools.py` pour extraction post-récupération HTML
- Robuste face au HTML malformé

### 2.4 Bibliothèque MCP : `mcp>=0.9.0`

**Justification :**
- Bibliothèque officielle Anthropic
- Types `Tool`, `TextContent`, `ImageContent` avec validation Pydantic
- Support stdio via `stdio_server()`

---

## 3. Gestion du Cycle de Vie du Browser

### 3.1 Initialisation Lazy

**Choix :** Le browser Playwright n'est démarré que lors du premier appel à un outil web

```python
async def _ensure_browser(self):
    if self.browser is None:
        self.playwright_instance = await async_playwright().start()
        self.browser = await self.playwright_instance.chromium.launch(headless=True)
        self.page = await self.browser.new_page()
```

**Justification :**
- **Performance** : Évite le coût de démarrage si seuls les outils non-web sont utilisés
- **Ressources** : Économie mémoire (~100-150MB) si browser non nécessaire
- **Déterministe** : `_ensure_browser()` appelé par dispatcher uniquement pour outils web

### 3.2 Mode Headless par Défaut

**Choix :** `headless=True` dans `chromium.launch()`

**Justification :**
- **Performance** : 20-30% plus rapide sans rendu graphique
- **Déploiement** : Compatible environnements serveur sans GUI (Docker, CI/CD)
- **Débogage** : Screenshots disponibles via `capture_screen` tool

**Configurable** : Facilement modifiable pour debug local (`headless=False`)

### 3.3 Réutilisation du Browser

**Choix :** Une seule instance browser/page pour toute la durée de vie du serveur

**Justification :**
- **Performance** : Démarrage browser = 1-2s, réutilisation = 0s
- **État partagé** : Permet navigation multi-étapes (ex: login puis scraping)
- **Cookies/Session** : Persistance automatique entre appels

**Trade-off assumé :** Pas d'isolation entre requêtes (acceptable pour usage mono-client)


## 4. Catalogue d'Outils

### 4.1 Outils Web

| Outil | Description | Justification du choix |
|-------|-------------|------------------------|
| `navigate_web` | Navigation URL avec timeout | Entrée universelle, gestion erreurs réseau |
| `capture_screen` | Screenshot (partiel/complet) | Débogage visuel, preuve d'exécution |
| `extract_links` | Extraction liens avec filtre texte | Navigation découverte, pagination détection |
| `fill_field` | Remplissage champ via sélecteur CSS | Formulaires, recherches |
| `click_element` | Clic via sélecteur CSS | Navigation interactive, pagination |
| `get_html` | Récupération HTML complet | Base pour extraction données |

**Choix CSS selectors** : Standard web, précis, supporté par Playwright et LLM

### 4.2 Outils de Scraping

| Outil | Description | Innovation |
|-------|-------------|------------|
| `analyze_and_extract_data` | Analyse HTML + génération sélecteurs + extraction | LLM génère les sélecteurs CSS automatiquement |
| `save_results` | Sauvegarde JSON | Persistance structurée |
| `done` | Signal de complétion | Feedback explicite de fin |

**Innovation clé** : `analyze_and_extract_data` délègue au LLM la création des sélecteurs
- Agent n'a pas besoin de connaître la structure
- S'adapte aux variations de layout
- Utilise LiteLLM (Gemini 2.5 Flash par défaut)

---

## 5. Dispatching et Routage

### 5.1 Séparation Outils Web vs Scraping

**Choix :** Deux dictionnaires séparés dans `tool_dispatcher.py`

```python
WEB_TOOLS = {"navigate_web": navigate_web, ...}
SCRAPING_TOOLS = {"analyze_and_extract_data": analyze_and_extract_data, ...}
```

**Justification :**
- **Clarté** : Distinction explicite des responsabilités
- **Conditional browser init** : `get_web_tool_names()` retourne uniquement les outils nécessitant le browser
- **Extensibilité** : Facile d'ajouter une 3ème catégorie (ex: DB_TOOLS)

### 5.2 Gestion d'Erreurs Centralisée

**Choix :** Try/catch dans `dispatch_tool()` avec retour TextContent standardisé

**Justification :**
- Erreurs remontées au client de manière uniforme
- Évite crash du serveur sur erreur outil
- Logging centralisé `[MCP] Tool execution error: ...`

---

## 6. Logging et Observabilité

### 6.1 Préfixe `[MCP]` Systématique

**Choix :** Tous les logs serveur préfixés `[MCP]`

```python
print(f"[MCP] Starting browser...")
print(f"[MCP] Executing tool: {name}")
```

**Justification :**
- Distinction logs serveur vs agent dans stdout partagé
- Facilite debugging multi-composants
- Grep-friendly : `grep "\[MCP\]" logs.txt`

### 6.2 Logs Structurés par Outil

**Pattern :**
```python
print(f"[MCP] Navigating to: {url}")  # Avant action
print(f"[MCP] Successfully navigated to: {url}")  # Succès
print(f"[MCP] Error navigating: {e}")  # Erreur
```

**Justification :** Traçabilité complète du workflow outil par outil