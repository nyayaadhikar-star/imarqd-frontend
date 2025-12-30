import os

def build_tree(root_dir, skip_dirs=None, prefix=""):
    """
    Builds the directory tree structure as a string.
    
    :param root_dir: The directory to start from.
    :param skip_dirs: List of folder names to skip.
    :param prefix: Used internally for indentation.
    :return: String containing the tree structure.
    """
    if skip_dirs is None:
        skip_dirs = []

    tree_str = ""
    entries = sorted(os.listdir(root_dir))
    entries_count = len(entries)

    for index, entry in enumerate(entries):
        path = os.path.join(root_dir, entry)
        connector = "├── " if index < entries_count - 1 else "└── "

        # Skip unwanted directories
        if entry in skip_dirs and os.path.isdir(path):
            continue

        tree_str += prefix + connector + entry + "\n"

        if os.path.isdir(path):
            extension = "│   " if index < entries_count - 1 else "    "
            tree_str += build_tree(path, skip_dirs, prefix + extension)

    return tree_str


if __name__ == "__main__":
    # Change this to your root directory
    root_directory = "."

    # Folders you want to skip
    skip_folders = ["node_modules", "__pycache__", ".git", ".venv"]

    # Build tree string
    tree_output = root_directory + "\n" + build_tree(root_directory, skip_folders)

    # Save into README.md
    with open("README_tree.md", "w", encoding="utf-8") as f:
        f.write("# Project Directory Tree\n\n")
        f.write("```\n")  # Markdown code block
        f.write(tree_output)
        f.write("```\n")

    print("✅ Directory tree saved to README_tree.md")
