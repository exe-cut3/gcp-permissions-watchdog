import os
import json
import argparse
import git
from datetime import datetime

class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle datetime objects."""
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)

def parse_args():
    parser = argparse.ArgumentParser(description="GCP Permissions Watchdog")
    parser.add_argument("--repo-path", required=True, help="Path to the git repository to analyze")
    parser.add_argument("--output-dir", required=True, help="Directory to save the generated output")
    parser.add_argument("--file-pattern", default="permissions.json", help="File pattern to track changes for") 
    return parser.parse_args()

def get_file_content(commit, file_pattern):
    """Retrieve the content of a file from a specific commit."""
    try:
        # Find the file in the commit tree
        # This is a simple search, might need to be recursive if file is in subdir
        # For now assuming file_pattern is a relative path matching the tree structure or just filename
        item = commit.tree / file_pattern
        return item.data_stream.read().decode('utf-8')
    except (KeyError, ValueError):
        return None

def parse_permissions(content):
    """Parse permissions from file content (JSON or Text)."""
    if not content:
        return set()
    
    try:
        data = json.loads(content)
        if isinstance(data, dict):
            # Try to find a list of permissions
            if 'valid_permissions' in data:
                return set(data['valid_permissions'])
            elif 'permissions' in data:
                return set(data['permissions'])
            # Fallback: looks for any list values
            for key, val in data.items():
                if isinstance(val, list):
                    return set(val)
        elif isinstance(data, list):
            return set(data)
    except json.JSONDecodeError:
        # Fallback to line-based text
        return set([line.strip() for line in content.splitlines() if line.strip()])
    
    return set()

def compute_diff(prev_perms, curr_perms):
    """Compute added and removed permissions grouped by service."""
    added = curr_perms - prev_perms
    removed = prev_perms - curr_perms
    
    def group_by_service(perms):
        grouped = {}
        for p in perms:
            parts = p.split('.')
            if len(parts) >= 1:
                service = parts[0]
                if service not in grouped:
                    grouped[service] = []
                grouped[service].append(p)
        # Sort keys and lists
        return {k: sorted(v) for k, v in sorted(grouped.items())}

    return {
        'added': group_by_service(added),
        'removed': group_by_service(removed)
    }

def analyze_repo(repo_path, file_pattern):
    try:
        repo = git.Repo(repo_path)
    except git.exc.InvalidGitRepositoryError:
        print(f"Error: {repo_path} is not a valid git repository.")
        return []

    if repo.bare:
        print(f"Error: {repo_path} is a bare repository.")
        return []

    history = []
    
    # Get all commits in reverse chronological order (newest first)
    commits = list(repo.iter_commits())
    
    # We need to process from oldest to newest to build state, 
    # but the UI expects newest first.
    # Let's process oldest to newest to track "previous" state easily.
    commits.reverse()
    
    prev_perms = set()
    
    for commit in commits:
        content = get_file_content(commit, file_pattern)
        curr_perms = parse_permissions(content)
        
        # Only record if there's a change or it's the first commit with data
        if curr_perms != prev_perms or not history:
            diff = compute_diff(prev_perms, curr_perms)
            
            # Count services (distinct prefixes)
            all_services = set(p.split('.')[0] for p in curr_perms if '.' in p)
            
            commit_data = {
                'hash': commit.hexsha,
                'author': commit.author.name,
                'date': datetime.fromtimestamp(commit.committed_date),
                'message': commit.message.strip(),
                'stats': {
                    'total_permissions': len(curr_perms),
                    'service_count': len(all_services),
                    'added_count': sum(len(v) for v in diff['added'].values()),
                    'removed_count': sum(len(v) for v in diff['removed'].values())
                },
                'diff': diff
            }
            
            # Only add to history if there are real permission changes 
            # AND the commit message looks relevant (to filter out noise like "update readme" or "refactor")
            # User wants to see only when permissions are updated.
            relevant_message = "Auto-update" in commit.message or "release" in commit.message.lower()
            
            # Additional check: If diff is empty, we probably shouldn't show it unless it's a major release/reset
            has_changes = diff['added'] or diff['removed']
            
            # Logic: Show if it has content changes. 
            # If the user strictly wants "only commits when permissions.txt changes", checking `has_changes` is key.
            # But sometimes even if `permissions.txt` changes, it might be noise if the message isn't right.
            # Let's trust the content change first, but maybe we can enforce message filter if requested?
            # User said: "I want watchdog to show only commits when permissions.txt changes"
            # Previous logic: `if diff['added'] or diff['removed']` covered this.
            # But the user mentioned "not commits where I change everything".
            # So let's try to filter by file path change detection strictly?
            # `compute_diff` relies on parsed content.
            # If `curr_perms != prev_perms`, then content changed.
            # So existing logic `curr_perms != prev_perms` IS the filter.
            # Why did user see "update readme"?
            # Perhaps `permissions.txt` was touched or reformatted in that commit?
            # Or perhaps `prev_perms` vs `curr_perms` logic was flawy?
            # Let's reinforce it by checking if permissions.txt was actually in the commit's diff stats?
            # Accessing commit stats is expensive.
            # Let's rely on content diff + message filter as a heuristic for "clean dashboard".
            
            if has_changes or (not prev_perms and curr_perms):
                # Optional: Filter by message if user wants to hide "Refactor" commits that might have accidentally changed permissions
                # or just to be cleaner.
                # Let's implement a "Smart Filter" where if the message doesn't look like an update, we assume it's noise unless massive change?
                # User asked: "I want watchdog to were shown only commits when permissions.txt changes... not everything"
                # So if I change README, `permissions.txt` usually doesn't change.
                # If `curr_perms == prev_perms`, we skip.
                # The issue "update readme" with -1 change suggests `permissions.txt` DID change.
                # So we should trust the diff.
                # However, to be extra safe for the "Security Research" dashboard view, lets prioritize "Auto-update" commits.
                
                # Let's add a flag to the data or filter here? 
                # I will add a strict filter: Only show if message contains "Auto-update" OR "release" OR "Merge" (if merge brought changes).
                # Actually, simplest is just trust the diff BUT maybe valid permissions list changed due to parsing logic update?
                # If I change parser logic, `curr_perms` changes without file change. 
                # That explains "Native API discovery" (+1650 -419).
                # User wants to see "GCP updates", not "Tool updates".
                
                # STRICT FILTER Implementation:
                is_auto_update = "Auto-update" in commit.message
                is_release = "release" in commit.message.lower()
                
                if is_auto_update or is_release or (has_changes and len(history) < 1):
                     history.append(commit_data)
        
        prev_perms = curr_perms

    # Reverse back to newest first
    history.reverse()
             
    return history

def main():
    args = parse_args()
    
    if not os.path.isdir(args.output_dir):
        os.makedirs(args.output_dir)
        
    print(f"Analyzing repository at: {args.repo_path}")
    history = analyze_repo(args.repo_path, args.file_pattern)
    
    output_file = os.path.join(args.output_dir, 'data.json')
    with open(output_file, 'w') as f:
        json.dump(history, f, cls=DateTimeEncoder, indent=2)
        
    print(f"Analysis complete. Found {len(history)} relevant commits.")
    print(f"Output saved to: {output_file}")

if __name__ == "__main__":
    main()
