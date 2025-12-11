# Contributing to StudyCase TW3 MCP Server

Thank you for your interest in contributing to this project! This guide will help you get started.

## Development Setup

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

## Development Workflow

### Building

The project uses TypeScript. To build:
```bash
npm run build
```

For development with auto-rebuild:
```bash
npm run watch
```

### Testing

Run the test suite:
```bash
npm test
```

This will:
1. Build the TypeScript code
2. Start the MCP server
3. Send test requests to verify all tools work correctly

### Running the Server

To run the server directly:
```bash
npm start
```

## Adding New Tools

To add a new tool to the MCP server:

1. **Define the tool schema** in `src/index.ts`:
```typescript
const TOOLS: Tool[] = [
  // ... existing tools
  {
    name: "your_tool_name",
    description: "Description of what your tool does",
    inputSchema: {
      type: "object",
      properties: {
        param1: {
          type: "string",
          description: "Description of parameter",
        },
      },
      required: ["param1"],
    },
  },
];
```

2. **Implement the tool handler** in the `CallToolRequestSchema` handler:
```typescript
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  switch (name) {
    // ... existing cases
    case "your_tool_name": {
      const param1 = args?.param1 as string;
      // Your implementation here
      return {
        content: [
          {
            type: "text",
            text: `Result: ${param1}`,
          },
        ],
      };
    }
  }
});
```

3. **Add tests** in `src/test.ts` to verify your tool works correctly

4. **Update documentation** in `README.md` to describe your new tool

## Code Style

- Use TypeScript for all code
- Follow the existing code style
- Use meaningful variable names
- Add comments for complex logic
- Keep functions focused and small

## Commit Guidelines

- Write clear, concise commit messages
- Start commit messages with a verb (Add, Fix, Update, etc.)
- Reference issue numbers when applicable

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes
3. Test your changes thoroughly
4. Update documentation as needed
5. Submit a pull request with a clear description

## Questions?

If you have questions or need help, please open an issue on GitHub.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
