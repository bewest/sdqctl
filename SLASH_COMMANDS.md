# GitHub Copilot CLI Slash Commands

This document provides a comprehensive reference for all available slash commands in the GitHub Copilot CLI.

## Session Management

### `/clear`, `/new`
Clear the conversation history and start a fresh session.

### `/compact`
Summarize conversation history to reduce context window usage. Useful when approaching context limits.

### `/context`
Show context window token usage and visualization. Displays how much of your context window is being used.

### `/exit`, `/quit`
Exit the CLI and return to your terminal.

## Directory & File Management

### `/cwd`, `/cd [directory]`
- Without arguments: Show the current working directory
- With directory: Change to the specified directory

**Usage:**
```
/cwd              # Show current directory
/cd src/          # Change to src/ directory
/cd ../           # Move up one level
```

### `/add-dir <directory>`
Add a directory to the allowed list for file access. Grants Copilot permission to access files in the specified directory.

**Usage:**
```
/add-dir /path/to/project
```

### `/list-dirs`
Display all allowed directories for file access. Shows which directories Copilot has permission to access.

## Configuration & Customization

### `/model [model]`
Select the AI model to use for your session.

**Available models:**
- Claude Sonnet 4.5 (default)
- Claude Sonnet 4
- Claude Haiku 4.5
- Claude Opus 4.5
- GPT-5
- GPT-5.1
- GPT-5.2
- And more

**Usage:**
```
/model                 # Show current model and available options
/model claude-opus-4.5 # Switch to Claude Opus 4.5
```

### `/theme [show|set|list] [auto|dark|light]`
View or configure the terminal theme.

**Usage:**
```
/theme show       # Display current theme
/theme list       # List available themes
/theme set dark   # Set dark theme
/theme set light  # Set light theme
/theme set auto   # Use system theme
```

### `/terminal-setup`
Configure your terminal for multiline input support (Shift+Enter and Ctrl+Enter).

## File Access Control

### `/deny-file <file>`
Temporarily deny access to a specific file during the current conversation session. Useful for protecting critical files during exploratory or automated operations.

**Usage:**
```
/deny-file package.json
/deny-file .env
/deny-file .env.production
```

### `/deny-path <pattern>`
Temporarily deny access to files matching a glob pattern during the current conversation session.

**Usage:**
```
/deny-path "*.key"
/deny-path "secrets/*"
/deny-path ".github/workflows/*"
/deny-path "config/production/*"
```

**Note:** File denials take precedence over allows, following the same model as `--deny-tool` and `--deny-url`. These settings persist only for the current session.

## Authentication

### `/login`
Log in to GitHub Copilot. Required on first use or if your session expires.

### `/logout`
Log out of GitHub Copilot.

### `/user [show|list|switch]`
Manage GitHub user accounts.

**Usage:**
```
/user show        # Show current user
/user list        # List all authenticated users
/user switch      # Switch between authenticated users
```

## Planning & Delegation

### `/plan [prompt]`
Create an implementation plan before coding. Useful for complex changes where you want to review the approach first.

**Usage:**
```
/plan Add authentication to the API
```

### `/delegate <prompt>`
Delegate changes to a remote repository with an AI-generated pull request. Copilot will create a branch, make changes, and open a PR.

**Usage:**
```
/delegate Fix the login bug in the authentication module
```

## Extensions & Integrations

### `/agent`
Browse and select from available agents (if any custom agents are configured).

### `/skills [list|info|add|remove|reload] [args...]`
Manage skills for enhanced capabilities. Skills provide specialized functionality.

**Usage:**
```
/skills list              # List all available skills
/skills info <skill-name> # Get info about a specific skill
/skills add <skill-path>  # Add a new skill
/skills remove <skill>    # Remove a skill
/skills reload            # Reload all skills
```

### `/mcp [show|add|edit|delete|disable|enable] [server-name]`
Manage Model Context Protocol (MCP) server configuration. MCP servers extend Copilot's capabilities.

**Usage:**
```
/mcp show                  # Show all MCP servers
/mcp add <server-name>     # Add a new MCP server
/mcp edit <server-name>    # Edit MCP server configuration
/mcp delete <server-name>  # Delete an MCP server
/mcp disable <server-name> # Disable an MCP server
/mcp enable <server-name>  # Enable an MCP server
```

## Information & Monitoring

### `/session [checkpoints [n]|files|plan]`
Show session information and workspace summary.

**Usage:**
```
/session            # Show overall session info
/session files      # Show files in current workspace
/session plan       # Show current plan (if any)
/session checkpoints # Show session checkpoints
/session checkpoints 5 # Show last 5 checkpoints
```

### `/usage`
Display session usage metrics and statistics, including token usage and API requests.

### `/context`
Show context window token usage and visualization.

## Sharing & Feedback

### `/share [file|gist] [path]`
Share your session to a markdown file or GitHub gist.

**Usage:**
```
/share file session.md    # Save to local file
/share gist               # Create a GitHub gist
```

### `/feedback`
Provide feedback about the CLI. Opens a confidential feedback survey.

## Help & Documentation

### `/help`
Show help for interactive commands and keyboard shortcuts.

## Advanced

### `/reset-allowed-tools`
Reset the list of allowed tools to default settings.

## Keyboard Shortcuts

While not slash commands, these shortcuts enhance your CLI experience:

- **@** - Mention files to include their contents in the current context
- **Esc** - Cancel the current operation
- **!** - Execute a command in your local shell without sending to Copilot
- **Ctrl+c** - Cancel operation if thinking, clear input if present, or exit
- **Ctrl+d** - Shutdown
- **Ctrl+l** - Clear the screen
- **Ctrl+o** - Expand all timeline/collapse timeline
- **Ctrl+r** - Expand recent timeline/collapse timeline
- **↑↓** - Navigate command history

### Motion Shortcuts

- **Ctrl+a** - Move to the beginning of the line
- **Ctrl+e** - Move to the end of the line
- **Ctrl+h** - Delete previous character
- **Ctrl+w** - Delete previous word
- **Ctrl+u** - Delete from cursor to beginning of line
- **Ctrl+k** - Delete from cursor to end of line
- **Meta+←/→** - Move cursor by word

## Additional Resources

- [Official Documentation](https://docs.github.com/copilot/concepts/agents/about-copilot-cli)
- [Using Copilot CLI](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/use-copilot-cli)
- [Copilot Plans](https://github.com/features/copilot/plans)
