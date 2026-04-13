## ADDED Requirements

### Requirement: ACP JSON-RPC transport over stdio
The system SHALL replace the custom JSONL protocol with ACP's JSON-RPC 2.0 transport. The `--rpc` CLI flag SHALL launch the ACP transport layer using `acp.run_agent()`.

#### Scenario: Launch RPC mode with --rpc flag
- **WHEN** user runs `codepi --rpc`
- **THEN** the process starts and listens for JSON-RPC 2.0 messages on stdin over the ACP transport

#### Scenario: Clean shutdown on stdin EOF
- **WHEN** the client closes stdin (EOF)
- **THEN** the agent process SHALL exit cleanly with code 0

### Requirement: Initialize handshake
The system SHALL implement the ACP `initialize` method. When a client sends an `initialize` JSON-RPC request, the agent SHALL respond with protocol version, agent capabilities, agent info, and available auth methods.

#### Scenario: Successful initialize handshake
- **WHEN** client sends `{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": 1, "clientCapabilities": {}, "clientInfo": {"name": "zed", "title": "Zed", "version": "0.1.0"}}}`
- **THEN** agent responds with `{"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": 1, "agentCapabilities": {"loadSession": true, "promptCapabilities": {"image": false, "audio": false, "embeddedContext": true}}, "agentInfo": {"name": "codepi", "title": "codepi", "version": "..."}, "authMethods": []}}`

#### Scenario: Initialize with unsupported protocol version
- **WHEN** client sends `initialize` with a protocol version that is not supported
- **THEN** agent SHALL respond with the latest supported protocol version it can use

### Requirement: Agent capabilities declaration
The system SHALL declare the following capabilities in the `initialize` response:
- `loadSession: true` (session loading is planned)
- `promptCapabilities.image: false` (no image support)
- `promptCapabilities.audio: false` (no audio support)
- `promptCapabilities.embeddedContext: true` (file context in prompts)

#### Scenario: Capabilities match declared values
- **WHEN** client receives the `initialize` response
- **THEN** `agentCapabilities.loadSession` SHALL be `true`
- **AND** `agentCapabilities.promptCapabilities.image` SHALL be `false`
- **AND** `agentCapabilities.promptCapabilities.audio` SHALL be `false`
- **AND** `agentCapabilities.promptCapabilities.embeddedContext` SHALL be `true`

### Requirement: Agent info declaration
The system SHALL identify itself as "codepi" in the `initialize` response.

#### Scenario: Agent info fields
- **WHEN** client receives the `initialize` response
- **THEN** `agentInfo.name` SHALL be `"codepi"`
- **AND** `agentInfo.title` SHALL be `"codepi"`
- **AND** `agentInfo.version` SHALL be a non-empty version string
- **AND** `authMethods` SHALL be an empty list

### Requirement: No impact on other modes
The replacement of the RPC mode SHALL NOT affect interactive mode, print mode, or SDK mode.

#### Scenario: Interactive mode unchanged
- **WHEN** user runs `codepi` (no --rpc flag)
- **THEN** interactive mode SHALL launch and behave identically to before the ACP change
