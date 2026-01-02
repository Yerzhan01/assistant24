import os
import re

def fix_sqlalchemy_mapped(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Regex to swap Optional[Mapped[T]] to Mapped[Optional[T]]
    # Handle simple types first: Optional[ Mapped[str ]] -> Mapped[Optional[str]]
    # Allowing for spaces
    
    pattern = r'Optional\[\s*Mapped\[\s*([a-zA-Z0-9_]+)\s*\]\s*\]'
    
    def replacer(match):
        inner_type = match.group(1)
        return f"Mapped[Optional[{inner_type}]]"
    
    new_content = re.sub(pattern, replacer, content)
    
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Fixed {filepath}")
        return True
    return False

def main():
    count = 0
    for root, dirs, files in os.walk("./backend/app/models"):
        for file in files:
            if file.endswith(".py"):
                if fix_sqlalchemy_mapped(os.path.join(root, file)):
                    count += 1
    print(f"Fixed {count} model files")

if __name__ == "__main__":
    main()
