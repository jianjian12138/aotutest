import os
import codecs

apps_dir = r'd:\TEST\apps'
for root, dirs, files in os.walk(apps_dir):
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'rb') as f:
                    content = f.read()
                if content.startswith(codecs.BOM_UTF8):
                    content = content[len(codecs.BOM_UTF8):]
                    with open(filepath, 'wb') as f:
                        f.write(content)
                    print(f"Removed BOM from {filepath}")
            except Exception as e:
                print(f"Error processing {filepath}: {e}")
