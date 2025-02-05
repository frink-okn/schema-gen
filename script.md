# README

## Overview
This script automates the process of generating schema documentation for a given graph and pushing the updates to a GitHub repository.

## Prerequisites
- Bash shell environment
- Python 3 installed
- Git installed and configured
- GitHub SSH access with a valid deploy key
- Required Python scripts available: `dump_yaml.py` and `docgen-frink.py`
- `gh` (GitHub CLI) installed and authenticated

## Usage
```bash
./script.sh <graph-name> <graph-data-path> <custom-graph-title> <git-branch>
```

### Arguments:
1. `<graph-name>`: Name of the graph.
2. `<graph-data-path>`: Path to the graph data.
3. `<custom-graph-title>`: Custom title for the graph.
4. `<git-branch>` (optional): Branch to push changes to (defaults to `main`).

## Script Functionality
1. **Validates Arguments:** Ensures the required arguments are provided.
2. **Sets Up SSH Configuration:**
   - Creates `~/.ssh` if not present.
   - Adds GitHub to `known_hosts`.
   - Configures and adds the SSH deploy key.
3. **Configures Git:** Sets user details and SSH command for authentication.
4. **Clones Repository:**
   - Clones `git@github.com:frink-okn/graph-descriptions.git`.
   - Checks out the specified branch or creates it if not existing.
5. **Runs Schema and Documentation Generation:**
   - Calls `dump_yaml.py` to generate the schema.
   - Calls `docgen-frink.py` to generate documentation.
6. **Commits and Pushes Changes to GitHub:**
   - Adds and commits updated documentation.
   - Pushes changes and creates a pull request using GitHub CLI.

## Expected Output
- Generated schema and documentation stored in the `repo/<graph-name>` directory.
- A pull request is automatically created for the updates.

## Troubleshooting
- Ensure the deploy key is correctly configured and has necessary permissions.
- Verify that the required Python scripts are available in the `src/` directory.
- Check GitHub CLI authentication (`gh auth status`).
- Ensure the correct repository permissions for pushing changes.

## License
This script is provided under the MIT License.

