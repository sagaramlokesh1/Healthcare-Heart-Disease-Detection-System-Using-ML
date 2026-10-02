import os
import re

templates_dir = 'frontend/templates'

for root, dirs, files in os.walk(templates_dir):
    for file in files:
        if file.endswith('.html'):
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            # Remove any line containing {% csrf_token %} (including commented ones)
            new_content = re.sub(r'^\s*<!--?\s*\{%\s*csrf_token\s*%\s*\}\s*--?>\s*\n?', '', content, flags=re.MULTILINE)
            new_content = re.sub(r'^\s*\{%\s*csrf_token\s*%\s*\}\s*\n?', '', new_content, flags=re.MULTILINE)
            # Replace Django {% url %} with Flask {{ url_for() }}
            new_content = re.sub(r'\{%\s*url\s+[\'"](\w+)[\'"]\s*%\}', r"{{ url_for('\1') }}", new_content)
            if new_content != content:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f'Cleaned {path}')