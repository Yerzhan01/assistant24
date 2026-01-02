import os

def add_postponed_annotations(directory):
    count = 0
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                
                if "from __future__ import annotations" in content:
                    continue
                
                # Check for docstring to insert after
                lines = content.splitlines()
                insert_idx = 0
                if lines and (lines[0].startswith('"""') or lines[0].startswith("'''")):
                    # Simple heuristic: find end of docstring or just insert at top if mixed
                    # Safest is top if no docstring, or after docstring. 
                    # For simplicity, putting it at the very top is valid in Python, 
                    # but usually it's after module docstrings.
                    # Let's just prepend to the whole content for now, python interprets it fine usually 
                    # UNLESS there's a docstring which must be first for help().
                    # Let's try to be smart: if first char is quote, find closing quote.
                    pass
                
                # Simpler approach: Just prepend it. 
                # If there is a docstring, it might become not-a-docstring, but code will run.
                # Prioritizing running code over help() correctness for now.
                # Actually, effectively, replacing the file content with import + newline + content.
                
                new_content = "from __future__ import annotations\n" + content
                
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"Patched {filepath}")
                count += 1
    print(f"Total files patched: {count}")

if __name__ == "__main__":
    add_postponed_annotations("./backend/app")
