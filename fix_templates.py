import os
import re

template_dir = 'frontend/templates/predictor'

for root, dirs, files in os.walk(template_dir):
    for file in files:
        if file.endswith('.html'):
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                original = f.read()
            # Remove backslashes that escaped single quotes
            content = original.replace("\\'", "'")
            # Replace Django {% url ... %} with Flask {{ url_for(...) }}
            content = re.sub(r"{% url '([^']+)' %}", r"{{ url_for('\1') }}", content)
            if content != original:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f'✅ Fixed {path}')