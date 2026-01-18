# copilot do - a proposal

copilot has an incredibly rich interactive mode.
It should have a classic cli mode, perhaps a subcommand called `do` that allows
orchestrating the coding agent on the command line.
Do should work as a cross between

This is a proposal for a `do` subcommand for github copilot.
The proposed `do` allows running one "conversational cycle" of the copilot
conversation engine up to `--max-conversation-cycles [1]` times.

Perhaps with additional plan and build subcommands.
There are two ideas to help using the cli to orchestrate coding agents on the
command line.  First, is the @SLASH_COMMANDS, and turning many if it not
most/all of them into a file format similar to Dockerfile, but for
CopilotConversationFiles.  The default could read `[.CopilotConversation]`,
which would be formatted with the slashcommands as keyword, similar to
Dockerfile.  Then these can be orchestrated across subdirectories and
directories and different components of projects in a meaningful way.


The second is to add options for command line use for the single "dev loop" use case like this, perhaps similar to pandoc.

```
copilot do [prompt]
# Eg: 
# Drop into interactive mode after interpreting the prompt/conversation
cat MyConversation
Let's evaluate tests and our test specs and requirements for this component.
# Dumps what it would do given this conversation
copilot plan ./MyConversation

# This will lead to things like:
for component in ./lib/component/*; do
  # deep audit
  # ensure everything is accurate
  copilot do ensure there is a mapping for $component in our documentation in @docs/ and that it is correcct.
  make verify-docs $component | copilot do --epilogue - make sure to update our @plans/$component-progress

done
```
And other workflows to iteratively work through and orchestrate the software
development lifecycle across different aspects and facets of their own
organizations, codebases, and tooling.
A cross between pandoc, git rebase/bisect, and dockerfile.
Ideas that come to mind copilot loop --json plans/* | tee results.json && make verify verified-results.json

For reference, the current `copilot --help`:

```
Usage: copilot [options] [command]

GitHub Copilot CLI - An AI-powered coding assistant

Options:
  --add-dir <directory>               Add a directory to the allowed list for
                                      file access (can be used multiple times)
  --add-github-mcp-tool <tool>        Add a tool to enable for the GitHub MCP
                                      server instead of the default CLI subset
                                      (can be used multiple times). Use "*" for
                                      all tools.
  --add-github-mcp-toolset <toolset>  Add a toolset to enable for the GitHub MCP
                                      server instead of the default CLI subset
                                      (can be used multiple times). Use "all"
                                      for all toolsets.
  --additional-mcp-config <json>      Additional MCP servers configuration as
                                      JSON string or file path (prefix with @)
                                      (can be used multiple times; augments
                                      config from ~/.copilot/mcp-config.json for
                                      this session)
  --agent <agent>                     Specify a custom agent to use
  --allow-all                         Enable all permissions (equivalent to
                                      --allow-all-tools --allow-all-paths
                                      --allow-all-urls)
  --allow-all-paths                   Disable file path verification and allow
                                      access to any path
  --allow-all-tools                   Allow all tools to run automatically
                                      without confirmation; required for
                                      non-interactive mode (env:
                                      COPILOT_ALLOW_ALL)
  --allow-all-urls                    Allow access to all URLs without
                                      confirmation
  --allow-tool [tools...]             Tools the CLI has permission to use; will
                                      not prompt for permission
  --allow-url [urls...]               Allow access to specific URLs or domains
  --available-tools [tools...]        Only these tools will be available to the
                                      model
  --banner                            Show the startup banner
  --config-dir <directory>            Set the configuration directory (default:
                                      ~/.copilot)
  --continue                          Resume the most recent session
  --deny-tool [tools...]              Tools the CLI does not have permission to
                                      use; will not prompt for permission
  --deny-url [urls...]                Deny access to specific URLs or domains,
                                      takes precedence over --allow-url
  --disable-builtin-mcps              Disable all built-in MCP servers
                                      (currently: github-mcp-server)
  --disable-mcp-server <server-name>  Disable a specific MCP server (can be used
                                      multiple times)
  --disable-parallel-tools-execution  Disable parallel execution of tools (LLM
                                      can still make parallel tool calls, but
                                      they will be executed sequentially)
  --disallow-temp-dir                 Prevent automatic access to the system
                                      temporary directory
  --enable-all-github-mcp-tools       Enable all GitHub MCP server tools instead
                                      of the default CLI subset. Overrides
                                      --add-github-mcp-toolset and
                                      --add-github-mcp-tool options.
  --excluded-tools [tools...]         These tools will not be available to the
                                      model
  -h, --help                          display help for command
  -i, --interactive <prompt>          Start interactive mode and automatically
                                      execute this prompt
  --log-dir <directory>               Set log file directory (default:
                                      ~/.copilot/logs/)
  --log-level <level>                 Set the log level (choices: "none",
                                      "error", "warning", "info", "debug",
                                      "all", "default")
  --model <model>                     Set the AI model to use (choices:
                                      "claude-sonnet-4.5", "claude-haiku-4.5",
                                      "claude-opus-4.5", "claude-sonnet-4",
                                      "gpt-5.2-codex", "gpt-5.1-codex-max",
                                      "gpt-5.1-codex", "gpt-5.2", "gpt-5.1",
                                      "gpt-5", "gpt-5.1-codex-mini",
                                      "gpt-5-mini", "gpt-4.1",
                                      "gemini-3-pro-preview")
  --no-auto-update                    Disable downloading CLI update
                                      automatically
  --no-color                          Disable all color output
  --no-custom-instructions            Disable loading of custom instructions
                                      from AGENTS.md and related files
  -p, --prompt <text>                 Execute a prompt in non-interactive mode
                                      (exits after completion)
  --plain-diff                        Disable rich diff rendering (syntax
                                      highlighting via diff tool specified by
                                      git config)
  --resume [sessionId]                Resume from a previous session (optionally
                                      specify session ID)
  -s, --silent                        Output only the agent response (no stats),
                                      useful for scripting with -p
  --screen-reader                     Enable screen reader optimizations
  --share [path]                      Share session to markdown file after
                                      completion in non-interactive mode
                                      (default: ./copilot-session-<id>.md)
  --share-gist                        Share session to a secret GitHub gist
                                      after completion in non-interactive mode
  --stream <mode>                     Enable or disable streaming mode (choices:
                                      "on", "off")
  -v, --version                       show version information
  --yolo                              Enable all permissions (equivalent to
                                      --allow-all-tools --allow-all-paths
                                      --allow-all-urls)

Commands:
  help [topic]                        Display help information

Help Topics:
  config       Configuration Settings
  commands     Interactive Mode Commands
  environment  Environment Variables
  logging      Logging
  permissions  Permissions

Examples:
  # Start interactive mode
  $ copilot

  # Start interactive mode and automatically execute a prompt
  $ copilot -i "Fix the bug in main.js"

  # Execute a prompt in non-interactive mode (exits after completion)
  $ copilot -p "Fix the bug in main.js" --allow-all-tools

  # Enable all permissions with a single flag
  $ copilot -p "Fix the bug in main.js" --allow-all
  $ copilot -p "Fix the bug in main.js" --yolo

  # Start with a specific model
  $ copilot --model gpt-5

  # Resume the most recent session
  $ copilot --continue

  # Resume a previous session using session picker
  $ copilot --resume

  # Resume with auto-approval
  $ copilot --allow-all-tools --resume

  # Allow access to additional directory
  $ copilot --add-dir /home/user/projects

  # Allow multiple directories
  $ copilot --add-dir ~/workspace --add-dir /tmp

  # Disable path verification (allow access to any path)
  $ copilot --allow-all-paths

  # Allow all git commands except git push
  $ copilot --allow-tool 'shell(git:*)' --deny-tool 'shell(git push)'

  # Allow all file editing
  $ copilot --allow-tool 'write'

  # Allow all but one specific tool from MCP server with name "MyMCP"
  $ copilot --deny-tool 'MyMCP(denied_tool)' --allow-tool 'MyMCP'

  # Allow GitHub API access (defaults to HTTPS)
  $ copilot --allow-url github.com

  # Deny access to specific domain over HTTPS
  $ copilot --deny-url https://malicious-site.com
  $ copilot --deny-url malicious-site.com

  # Allow all URLs without confirmation
  $ copilot --allow-all-urls

```
