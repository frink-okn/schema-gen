# README: Schema and Documentation Generation Script

## Overview

This script automates the process of generating a schema from a graph data folder and then creating documentation for the generated schema. It also manages versioning by pushing the documentation to a specified GitHub repository.

## Prerequisites

Ensure you have the following installed and configured before running the script:

- Python 3
- Git
- Necessary Python dependencies for `dump_yaml.py` and `docgen-frink.py`
- A GitHub repository to store the generated documentation
- A GitHub personal access token (PAT) stored in the `GITHUB_TOKEN` environment variable

## Usage

Run the script using the following command:

```bash
./script.sh <graph-name> <graph-data-path> [custom-graph-title] [git-branch]
```

### Arguments

- `<graph-name>`: Name of the graph.
- `<graph-data-path>`: Path to the graph data folder.
- `[custom-graph-title]` (optional): Custom title for the graph (defaults to `<graph-name>`).
- `[git-branch]` (optional): The Git branch to push updates to (defaults to `main`).

## Script Workflow

1. **Authentication**: Ensures `GITHUB_TOKEN` is set and configures Git credentials.
2. **Clone Repository**: Pulls the latest version of the documentation repository.
3. **Schema Generation**: Runs `dump_yaml.py` to generate a schema YAML file.
4. **Documentation Generation**: Runs `docgen-frink.py` to create markdown documentation.
5. **Push Updates**:
   - Locates the directory matching `<graph-name>` in the repository.
   - Clears existing content and replaces it with the new documentation.
   - Commits and pushes changes to the specified GitHub branch.

## Example

```bash
export GITHUB_TOKEN=your_personal_access_token
./script.sh my-graph /path/to/graph/data "My Custom Graph" develop
```

## Notes

- Ensure `GITHUB_TOKEN` has push access to the repository.
- The script creates and commits files in the `repo/<graph-name>` directory.
- Modify the repository URL inside the script before running it.

## Troubleshooting

- **Authentication Error**: Ensure `GITHUB_TOKEN` is correctly set.
- **Push Failure**: Verify repository permissions and branch existence.
- **Missing Dependencies**: Install required Python dependencies before execution.

