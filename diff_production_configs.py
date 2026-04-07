"""
Script to compare configs from SANDAG/ABM release or branch with configs from ActivitySim/sandag-abm3-example repo
"""

import os
import sys
import shutil
import tempfile
import subprocess
import zipfile
import requests
import argparse
from pathlib import Path


def get_latest_release(repo_owner, repo_name):
    """Fetch the latest release tag from GitHub API"""
    api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        return response.json()['tag_name']
    except Exception as e:
        print(f"Error fetching latest release: {e}")
        return None


def run_command(cmd, cwd=None):
    """Run a shell command and return the output"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {cmd}")
        print(f"Error: {e.stderr}")
        sys.exit(1)


def download_archive(url, dest_dir):
    """Download the archive from GitHub releases"""
    print(f"Downloading archive from {url}...")
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    zip_path = dest_dir / "archive.zip"
    with open(zip_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    print(f"Downloaded to {zip_path}")
    return zip_path


def clone_production_repo(repo_url, dest_dir, branch):
    """Clone the production repository at a specific branch"""
    clone_cmd = f"git clone {repo_url} --branch {branch} production_repo"
    
    print(f"Cloning production repo {repo_url} (branch: {branch})...")
    run_command(clone_cmd, cwd=dest_dir)
    return dest_dir / "production_repo"


def extract_configs(zip_path, extract_dir):
    """Extract src/asim/configs folder from the release"""
    print("Extracting configs folder...")
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        # List all files to find the correct path structure
        all_files = zip_ref.namelist()
        
        # Find files matching the pattern
        config_files = [f for f in all_files if 'src/asim/configs' in f]
        
        if not config_files:
            print("Warning: Could not find src/asim/configs in archive")
            print("Looking for alternative paths...")
            config_files = [f for f in all_files if 'configs' in f or 'configs/' in f]
        
        if not config_files:
            print("Available paths in archive:")
            for f in all_files[:20]:  # Show first 20 files
                print(f"  {f}")
            raise ValueError("Could not find configs folder in the archive")
        
        # Extract matching files
        for file in config_files:
            zip_ref.extract(file, extract_dir)
    
    # Find the extracted configs directory
    configs_path = None
    for root, dirs, files in os.walk(extract_dir):
        if root.endswith('configs') or (os.path.basename(root) == 'configs'):
            configs_path = Path(root)
            break
    
    if not configs_path:
        raise ValueError("Could not locate extracted configs folder")
    
    print(f"Extracted configs to {configs_path}")
    return configs_path


def clone_example_repo(repo_url, dest_dir, branch=None):
    """Clone the example repository"""
    clone_cmd = f"git clone {repo_url} example_repo"
    if branch:
        clone_cmd += f" --branch {branch}"

    print(f"Cloning example repo {repo_url}" + (f" (branch: {branch})" if branch else " (default branch)") + "...")
    run_command(clone_cmd, cwd=dest_dir)
    return dest_dir / "example_repo"


def perform_diff(production_dir, example_dir, summary_only=True, subdir=None):
    """Perform git diff between the two directories"""
    print("\n" + "="*80)
    print("PERFORMING DIFF")
    print("="*80 + "\n")
    
    # Copy production configs to example repo for comparison
    # Find a suitable subdirectory in example repo to compare against
    example_configs = example_dir / "configs"

    if not example_configs.exists():
        print(f"Warning: {example_configs} does not exist in example repo")
        print("Available directories:")
        for item in example_dir.iterdir():
            if item.is_dir():
                print(f"  {item.name}")
        return
    
    # If subdirectory specified, navigate to it
    if subdir:
        production_dir = production_dir / subdir
        example_configs = example_configs / subdir

        if not production_dir.exists():
            print(f"Error: Subdirectory '{subdir}' not found in production configs at {production_dir}")
            print(f"Available subdirectories in production:")
            parent = production_dir.parent
            for item in parent.iterdir():
                if item.is_dir():
                    print(f"  {item.name}")
            return

        if not example_configs.exists():
            print(f"Error: Subdirectory '{subdir}' not found in example configs at {example_configs}")
            print(f"Available subdirectories in example:")
            parent = example_configs.parent
            for item in parent.iterdir():
                if item.is_dir():
                    print(f"  {item.name}")
            return
    
    # Use git diff to compare
    print(f"Comparing:")
    print(f"  Production: {production_dir}")
    print(f"  Example: {example_configs}")
    print("\n" + "-"*80 + "\n")
    
    # Perform diff using git directly on both directories
    try:
        if summary_only:
            # Show only file names and status
            result = subprocess.run(
                ['git', 'diff', '--no-index', '--name-status', str(example_configs), str(production_dir)],
                cwd=example_dir,
                capture_output=True,
                text=True
            )
        else:
            # Show full diff
            result = subprocess.run(
                ['git', 'diff', '--no-index', str(example_configs), str(production_dir)],
                cwd=example_dir,
                capture_output=True,
                text=True
            )
        
        # git diff returns exit code 1 when differences exist, which is expected
        if result.stdout:
            if summary_only:
                print("Files with differences (M=Modified, A=Added, D=Deleted):\n")
            print(result.stdout)
        elif result.returncode == 0:
            print("No differences found between the configurations!")
        else:
            print(f"Error performing diff: {result.stderr}")
    except Exception as e:
        print(f"Error running git diff: {e}")


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Compare SANDAG/ABM release configs with ActivitySim example repo',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
            Examples:
            %(prog)s                                    # Use latest production release vs default example branch
            %(prog)s -p v15.3.1                         # Use specific production release
            %(prog)s -p develop                         # Use production develop branch
            %(prog)s -p main -e develop                 # Compare production main vs example develop
            %(prog)s -p v15.3.1 -e main -d resident     # Specific release vs example main, resident subdir only
            %(prog)s -p develop -d resident -f          # Production develop branch, full diff output
        """
    )
    parser.add_argument(
        '-p', '--production',
        type=str,
        default=None,
        help='SANDAG/ABM reference to compare: release tag (e.g., v15.3.1) or branch name (e.g., develop, main). If not specified, uses the latest release.'
    )
    parser.add_argument(
        '-e', '--example',
        type=str,
        default=None,
        help='ActivitySim/sandag-abm3-example branch to diff against (e.g., main, develop). If not specified, uses the default branch.'
    )
    parser.add_argument(
        '-f', '--full',
        action='store_true',
        help='Show full diff output instead of just file names (summary mode is default).'
    )
    parser.add_argument(
        '-d', '--subdir',
        type=str,
        default=None,
        help='Subdirectory within configs to diff (e.g., resident, commercial). If not specified, diffs entire configs directory.'
    )
    
    args = parser.parse_args()
    
    # Configuration
    REPO_OWNER = "SANDAG"
    REPO_NAME = "ABM"
    PRODUCTION_REPO_URL = f"https://github.com/{REPO_OWNER}/{REPO_NAME}.git"
    EXAMPLE_REPO_URL = "https://github.com/ActivitySim/sandag-abm3-example.git"
    
    # Determine production: release or branch
    # Check if it's a release tag (starts with 'v') or a branch name
    if args.production:
        source_ref = args.production
        # Heuristic: if it starts with 'v' and contains numbers, likely a release tag
        use_release = source_ref.startswith('v') and any(char.isdigit() for char in source_ref)
        
        if use_release:
            print(f"Using production release: {source_ref}")
        else:
            print(f"Using production branch: {source_ref}")
    else:
        # Default: fetch latest release
        print("Fetching latest release...")
        source_ref = get_latest_release(REPO_OWNER, REPO_NAME)
        if not source_ref:
            print("Error: Could not fetch latest release. Please specify with -p/--production")
            sys.exit(1)
        print(f"Using latest release: {source_ref}")
        use_release = True
    # Create temporary working directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        print(f"Working directory: {temp_path}\n")
        
        try:
            if use_release:
                # Step 1: Download release
                ARCHIVE_URL = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/archive/refs/tags/{source_ref}.zip"
                zip_path = download_archive(ARCHIVE_URL, temp_path)
                
                # Step 2: Extract configs
                configs_dir = extract_configs(zip_path, temp_path)
            else:
                # Step 1: Clone production repo at specific branch
                production_repo = clone_production_repo(PRODUCTION_REPO_URL, temp_path, source_ref)

                # Step 2: Find configs directory
                configs_dir = production_repo / "src" / "asim" / "configs"
                if not configs_dir.exists():
                    print(f"Error: Could not find configs at {configs_dir}")
                    sys.exit(1)
                print(f"Using configs from {configs_dir}")

            # Step 3: Clone example repo
            example_repo = clone_example_repo(EXAMPLE_REPO_URL, temp_path, args.example)
            # Step 4: Perform diff
            perform_diff(configs_dir, example_repo, summary_only=not args.full, subdir=args.subdir)

            print("\n" + "="*80)
            print("DIFF COMPLETE")
            print("="*80)
            
        except Exception as e:
            print(f"\nError: {e}")
            sys.exit(1)


if __name__ == "__main__":
    # Check for required tools
    required_tools = ['git']
    for tool in required_tools:
        if shutil.which(tool) is None:
            print(f"Error: {tool} is not installed or not in PATH")
            sys.exit(1)
    
    main()