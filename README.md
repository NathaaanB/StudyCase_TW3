# StudyCase_TW3 MCP Server

A Model Context Protocol (MCP) server implementation for StudyCase TW3. This server provides various tools that can be used by MCP clients to perform operations.

## Features

This MCP server provides the following tools:

- **get_time**: Get the current time in ISO format
- **echo**: Echo back a provided message
- **calculate**: Perform basic arithmetic operations (add, subtract, multiply, divide)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/NathaaanB/StudyCase_TW3.git
cd StudyCase_TW3
```

2. Install dependencies:
```bash
npm install
```

3. Build the project:
```bash
npm run build
```

## Usage

### Running the Server

Start the server using:
```bash
npm start
```

Or for development with auto-rebuild:
```bash
npm run watch
```

### Configuration for MCP Clients

To use this server with an MCP client (like Claude Desktop), add the following configuration:

#### Claude Desktop Configuration

Add to your Claude Desktop configuration file:

**MacOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "studycase-tw3": {
      "command": "node",
      "args": ["/absolute/path/to/StudyCase_TW3/dist/index.js"]
    }
  }
}
```

Replace `/absolute/path/to/StudyCase_TW3` with the actual path to your repository.

## Available Tools

### 1. get_time

Returns the current time in ISO 8601 format.

**Input**: None

**Example Response**:
```
Current time: 2024-01-15T10:30:45.123Z
```

### 2. echo

Echoes back the message you provide.

**Input**:
- `message` (string, required): The message to echo

**Example Response**:
```
Echo: Hello, World!
```

### 3. calculate

Performs basic arithmetic calculations.

**Input**:
- `operation` (string, required): One of "add", "subtract", "multiply", "divide"
- `a` (number, required): The first number
- `b` (number, required): The second number

**Example Response**:
```
Result: 10 add 5 = 15
```

## Development

### Project Structure

```
StudyCase_TW3/
├── src/
│   └── index.ts          # Main server implementation
├── dist/                 # Compiled JavaScript output
├── package.json          # Project dependencies
├── tsconfig.json         # TypeScript configuration
└── README.md            # This file
```

### Scripts

- `npm run build`: Compile TypeScript to JavaScript
- `npm start`: Run the compiled server
- `npm run dev`: Build and run the server
- `npm run watch`: Watch mode for development

### Adding New Tools

To add a new tool:

1. Define the tool in the `TOOLS` array with its schema
2. Add a case in the `CallToolRequestSchema` handler
3. Implement the tool logic
4. Rebuild the project

## Model Context Protocol (MCP)

This server implements the Model Context Protocol, which allows AI models to interact with external tools and data sources in a standardized way. For more information about MCP, visit the [official documentation](https://modelcontextprotocol.io).

## License

MIT
