# Test_Technique_TW3
Repository de l'agent IA et du serveur MCP construit dans le cadre du test technique de TW3 Partners.


- # Serveur MCP ('mcp_server/')
On y retrouve le serveur MCP avec les différents outils utiles pour l'agent IA tel que navigate_web, screenshot...

- # Agent IA ('scraper_agent_autonomous.py' and 'prompts_autonomous_scraper.py')
Le premier fichier est le code qui permet de faire des requêtes à un LLM et qui garde en mémoire les logs et les actions. Le second génère un prompt adapté et pertinent pour le LLM afin d'obtenir les résultats souhaités dans le format demandé.

- # Test ('test\')
Le dossier test comptend un prompt utilisé avec le serveur MCP et le dossier screenshot contient les 2 screenshots effectués.

- # Test agent IA
Le fichier 'schema_books_toscrape.json' contient une requête type que l'on peut demander à l'agent IA. L'agent ia peut être appelé avec "python scraper_agent_autonomous.py --config schema_books_toscrape.json --output results.json"

