# CLI Entry Point with Typer Framework

## Goal
CLI Entry Point with Typer Framework: Implement the main Typer application entry point in canon/cli/main.py that registers all command groups and provides the top-level canon CLI.

## Acceptance Criteria
- Given canon is installed, when the user runs canon with no arguments, then the Typer help output lists all four command groups (get, plan, rules, and status)
- Given the user runs canon --help, when the output is inspected, then each command group name and its one-line description are displayed
- Given the user runs canon invalid-command, when the command executes, then it exits with a non-zero code and prints a helpful error message listing valid commands
- Given the user runs canon --version, when the output is inspected, then it displays the installed canon package version string
- Given the Typer app is constructed in canon/cli/main.py, when the module is imported, then no CanonConfigError or other startup exceptions are raised unless canon.yaml is explicitly validated

## Constraints
- Complexity: low
