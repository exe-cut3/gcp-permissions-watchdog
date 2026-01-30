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
            
            # Only add to history if there are actual permission changes 
            # OR if it's the first commit and has permissions
            if diff['added'] or diff['removed'] or (not prev_perms and curr_perms):
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
