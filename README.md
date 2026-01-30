# GCP Permissions Watchdog

**GCP Permissions Watchdog** is a tool designed to visualize the evolution of Google Cloud Platform (GCP) permissions over time. It continuously monitors a git repository containing permission dumps (e.g., from `gcp-permissions-checker`) and generates a modern, interactive dashboard to highlight changes.

## Features

- **🔍 Deep Content Diffing**:
  Instead of just showing file changes, Watchdog parses the actual JSON or text content of your permission files to calculate exact additions and removals.

- **📊 Modern Dashboard**:
  - **Master-Detail Layout**: Browse history snapshots in a sidebar and view deep details in a dedicated pane.
  - **Service Impact Summary**: Instantly see which services are most affected (e.g., `aiplatform: +27 new, -5 removed`).
  - **GitHub-Style Diffs**: Clear green/red visualization for added and removed permissions.

- **📈 Statistics**:
  - Total Permission Count
  - Distinct Service Count
  - Net Change per Commit

- **🚀 Automated Deployment**:
  - Built-in GitHub Actions workflow to run analysis daily.
  - Automatically deploys the dashboard to GitHub Pages.

## How It Works

1.  **Watchdog Script (`watchdog.py`)**:
    - Clones/Pulls the target "Data Repository" (where you commit your permission lists).
    - Iterates through the git commit history.
    - Parses the permission file at each commit.
    - Computes granular differences between snapshots.
    - Generates a `data.json` file for the frontend.

2.  **Frontend**:
    - A static HTML/JS Single Page Application (SPA) loads `data.json`.
    - Renders the interactive timeline and diff views.

## Quick Start

### Prerequisites
- Python 3.8+
- Git

### Installation

1.  Clone this repository:
    ```bash
    git clone https://github.com/exe-cut3/gcp-permissions-watchdog.git
    cd gcp-permissions-watchdog
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### Local Usage

To run the watchdog against a local repository:

```bash
python3 watchdog.py \
  --repo-path /path/to/your/permissions-data-repo \
  --file-pattern permissions.txt \
  --output-dir static
```

- `--repo-path`: Path to the git repo you want to analyze.
- `--file-pattern`: The filename (or glob) to track within that repo.
- `--output-dir`: Where to generate the `data.json` (usually `static`).

Once generated, serve the `static` folder:

```bash
cd static
python3 -m http.server 8080
# Open http://localhost:8080 in your browser
```

## CI/CD Setup

This repository includes a GitHub Actions workflow (`.github/workflows/watchdog.yml`) that:
1.  Runs daily (cron `0 0 * * *`).
2.   checks out the target data repository.
3.  Runs the analysis.
4.  Deploys the result to **GitHub Pages**.

### Configuration
Update `.github/workflows/watchdog.yml` to point to your specific data repository:

```yaml
- name: Checkout Data Repo
  uses: actions/checkout@v4
  with:
    repository: <YOUR_USERNAME>/<YOUR_DATA_REPO>
    path: data-repo
    fetch-depth: 0 # Important for history
```

## License

MIT
