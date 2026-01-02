import os
import re

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Imports to check/add
    imports_needed = set()
    
    # Regex replacements
    
    # 1. Replace "Type | None" with "Optional[Type]"
    # Handles: : str | None, -> int | None, Mapped[str | None]
    # We need to be careful about nesting.
    # Simple case: word | None
    
    def replace_optional(match):
        imports_needed.add("Optional")
        return f"Optional[{match.group(1)}]"
    
    content = re.sub(r'([a-zA-Z0-9_\[\], ]+)\s*\|\s*None', replace_optional, content)
    
    # 2. Replace "Type | Other" with "Union[Type, Other]"
    # This is harder with regex, let's skip complex unions for now and focus on crashes.
    # Most crashes are Optional.
    
    # 3. Replace list[...] with List[...] and dict[...] with Dict[...]
    # SQLAlchemy eval() fails on list[] in 3.9
    
    def replace_list(match):
        imports_needed.add("List")
        return f"List[{match.group(1)}]"
    
    content = re.sub(r'\blist\[', 'List[', content)
    if "List[" in content: imports_needed.add("List")

    content = re.sub(r'\bdict\[', 'Dict[', content)
    if "Dict[" in content: imports_needed.add("Dict")
    
    # Add imports if changed
    if content != original_content:
        # Check current imports
        lines = content.splitlines()
        typing_line_idx = -1
        last_import_idx = 0
        
        existing_typing_imports = set()
        
        for i, line in enumerate(lines):
            if line.startswith("from typing import"):
                typing_line_idx = i
                # Extract existing
                parts = line.replace("from typing import", "").split(",")
                for p in parts:
                    existing_typing_imports.add(p.strip())
            if line.startswith("import ") or line.startswith("from "):
                last_import_idx = i
        
        items_to_add = [item for item in imports_needed if item not in existing_typing_imports]
        
        if items_to_add:
            if typing_line_idx != -1:
                # Append to existing typing import
                # Simple crude append
                lines[typing_line_idx] = lines[typing_line_idx].strip() + ", " + ", ".join(items_to_add)
            else:
                # Add new import line
                lines.insert(last_import_idx + 1, f"from typing import {', '.join(items_to_add)}")
        
        final_content = "\n".join(lines)
        if not final_content.endswith("\n"):
             final_content += "\n"
             
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(final_content)
        print(f"Fixed {filepath}")
        return True
    return False

def main():
    count = 0
    for root, dirs, files in os.walk("./backend/app"):
        for file in files:
            if file.endswith(".py"):
                if fix_file(os.path.join(root, file)):
                    count += 1
    print(f"Total files fixed: {count}")

if __name__ == "__main__":
    main()
