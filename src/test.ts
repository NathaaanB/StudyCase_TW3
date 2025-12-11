#!/usr/bin/env node

/**
 * Simple test script to verify MCP server communication
 * This simulates an MCP client sending requests to the server
 */

import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Start the MCP server
const serverPath = join(__dirname, '..', 'dist', 'index.js');
const server = spawn('node', [serverPath]);

let responseBuffer = '';

server.stdout.on('data', (data) => {
  responseBuffer += data.toString();
  
  // Try to parse complete JSON-RPC messages
  const lines = responseBuffer.split('\n');
  responseBuffer = lines.pop() || ''; // Keep incomplete line in buffer
  
  for (const line of lines) {
    if (line.trim()) {
      try {
        const response = JSON.parse(line);
        console.log('Server response:', JSON.stringify(response, null, 2));
      } catch (e) {
        console.log('Raw output:', line);
      }
    }
  }
});

server.stderr.on('data', (data) => {
  console.error('Server stderr:', data.toString());
});

server.on('close', (code) => {
  console.log(`Server process exited with code ${code}`);
});

// Send test requests
function sendRequest(request: any) {
  console.log('Sending request:', JSON.stringify(request, null, 2));
  server.stdin.write(JSON.stringify(request) + '\n');
}

// Wait a bit for server to initialize
setTimeout(() => {
  // Test 1: Initialize
  sendRequest({
    jsonrpc: '2.0',
    id: 1,
    method: 'initialize',
    params: {
      protocolVersion: '2024-11-05',
      capabilities: {},
      clientInfo: {
        name: 'test-client',
        version: '1.0.0',
      },
    },
  });

  // Test 2: List tools
  setTimeout(() => {
    sendRequest({
      jsonrpc: '2.0',
      id: 2,
      method: 'tools/list',
      params: {},
    });
  }, 1000);

  // Test 3: Call get_time tool
  setTimeout(() => {
    sendRequest({
      jsonrpc: '2.0',
      id: 3,
      method: 'tools/call',
      params: {
        name: 'get_time',
        arguments: {},
      },
    });
  }, 2000);

  // Test 4: Call echo tool
  setTimeout(() => {
    sendRequest({
      jsonrpc: '2.0',
      id: 4,
      method: 'tools/call',
      params: {
        name: 'echo',
        arguments: {
          message: 'Hello from test!',
        },
      },
    });
  }, 3000);

  // Test 4b: Call echo tool with empty string
  setTimeout(() => {
    sendRequest({
      jsonrpc: '2.0',
      id: '4b',
      method: 'tools/call',
      params: {
        name: 'echo',
        arguments: {
          message: '',
        },
      },
    });
  }, 3500);

  // Test 5: Call calculate tool
  setTimeout(() => {
    sendRequest({
      jsonrpc: '2.0',
      id: 5,
      method: 'tools/call',
      params: {
        name: 'calculate',
        arguments: {
          operation: 'add',
          a: 10,
          b: 5,
        },
      },
    });
  }, 4500);

  // Close after all tests
  setTimeout(() => {
    console.log('\nAll tests completed. Closing server...');
    server.kill();
    process.exit(0);
  }, 6000);
}, 500);

// Handle cleanup on exit
process.on('SIGINT', () => {
  server.kill();
  process.exit(0);
});
