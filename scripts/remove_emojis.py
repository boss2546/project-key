"""
Remove all display emojis from frontend files.
Keeps box-drawing characters (═══, ───) in comments.
"""
import re

# Match only real emojis (not box-drawing decorators)
emoji_pattern = re.compile(
    '['
    '\U0001F300-\U0001F9FF'  # Misc Symbols, Emoticons, Supplemental Symbols
    '\U00002600-\U000026FF'  # Misc symbols (⚡☀️ etc)  
    '\U00002700-\U000027BF'  # Dingbats (✓✕ etc)
    '\U0001FA00-\U0001FA6F'  # Chess symbols
    '\U0001FA70-\U0001FAFF'  # Symbols extended
    '\U0000FE00-\U0000FE0F'  # Variation selectors
    '\U0000200D'             # Zero width joiner
    '\U00002B50'             # Star
    ']+', re.UNICODE)

files = [
    'legacy-frontend/index.html',
    'legacy-frontend/app.js',
]

for filepath in files:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_len = len(content)
    
    # Remove emojis
    cleaned = emoji_pattern.sub('', content)
    
    # Clean up leftover double spaces from emoji removal
    # But be careful not to collapse intentional whitespace
    cleaned = re.sub(r'  +', ' ', cleaned)  # collapse multiple spaces to one
    # But preserve indentation (leading spaces)
    lines = cleaned.split('\n')
    final_lines = []
    for line in lines:
        # Don't collapse leading whitespace
        stripped = line.lstrip()
        if stripped:
            indent = line[:len(line) - len(stripped)]
            # Only collapse spaces within the content, not the indent
            final_lines.append(indent + re.sub(r'  +', ' ', stripped))
        else:
            final_lines.append(line)
    cleaned = '\n'.join(final_lines)
    
    new_len = len(cleaned)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(cleaned)
    
    removed = original_len - new_len
    print(f"✓ {filepath}: removed {removed} emoji characters")

print("\nDone! All emojis removed from frontend files.")
