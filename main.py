import os
import json
import shutil
import datetime

files = os.listdir("Keep")
json_files = []
for file in files:
    if file.endswith('.json'):
        json_files.append(file)

class Attachment:
    def __init__(self, mimetype, path):
        self.mimetype = mimetype
        self.path = path

class Annotation:
    def __init__(self, description, source, title, url):
        self.description = description
        self.source = source
        self.title = title
        self.url = url

class Note:
    def __init__(self, title, content, attachments, annotations, labels, created_timestamp):
        self.title = title
        self.content = content
        self.attachments = attachments
        self.annotations = annotations
        self.labels = labels
        self.created_timestamp = created_timestamp

notes = []

for file in json_files:
    try:
        with open("Keep/"+file, "r", encoding='utf-8') as f:
            text = f.read()
        try:
            data = json.loads(text)
        except json.JSONDecodeError as je:
            print(f"JSON parsing error in file {file}: {je}")
            continue
        except Exception as e:
            print(f"Unexpected error parsing {file}: {e}")
            continue

        title = ""
        content = ""
        attachments = []
        annotations = []
        labels = []

        if "title" in data:
            title = data["title"]
        
        if "textContent" in data:
            content = data["textContent"]

        if "attachments" in data:
            for attachment in data["attachments"]:
                mimetype = attachment["mimetype"]
                path = attachment["filePath"]
                attachments.append(Attachment(mimetype, path))

        if "annotations" in data:
            for annotation in data["annotations"]:
                description = annotation["description"]
                source = annotation["source"]
                title = annotation["title"]
                url = annotation["url"]
                annotations.append(Annotation(description, source, title, url))

        if "labels" in data:
            for label in data["labels"]:
                labels.append(label["name"])
        else:
            labels.append("NO_LABEL")
            
        # Add ARCHIVED label if note is archived
        if data.get("isArchived", False):
            labels.append("ARCHIVED")
        
        created_timestamp = data.get("createdTimestampUsec", 0)
        
        notes.append(Note(title, content, attachments, annotations, labels, created_timestamp))
    except Exception as e:
        print(f"Error processing file {file}: {str(e)}")
        import traceback
        print(traceback.format_exc())

labels = []

for note in notes:
    for label in note.labels:
        if label not in labels:
            labels.append(label)

for label in labels:
    exec(f"{label} = []")

for note in notes:
    for label in note.labels:
        exec(f"{label}.append(note)")
        exec(f"{label} = list(set({label}))")
        exec(f"{label} = sorted({label}, key=lambda x: x.created_timestamp, reverse=True)")

def sanitize_filename(filename):
    invalid_chars = '<>:"/\\|?*\n'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    filename = filename.strip('. ')
    if not filename:
        filename = 'untitled'
    return filename

def get_unique_filename(base_filename, existing_files):
    if base_filename not in existing_files:
        existing_files.add(base_filename)
        return base_filename
    
    counter = 1
    while True:
        new_filename = f"{base_filename}_{counter}"
        if new_filename not in existing_files:
            existing_files.add(new_filename)
            return new_filename
        counter += 1

def encode_markdown_text(text):
    replacements = {
        '[': '\\[',
        ']': '\\]',
        '(': '\\(',
        ')': '\\)',
        '_': '\\_',
        '*': '\\*',
        '#': '\\#',
        '|': '\\|',
        '<': '&lt;',
        '>': '&gt;',
        '`': '\\`',
        '"': '&quot;',
        "'": '&apos;'
    }
    for char in replacements.values():
        text = text.replace(char, char[-1])
    for char, encoded in replacements.items():
        text = text.replace(char, encoded)
    return text

def encode_url(url):
    from urllib.parse import quote
    from urllib.parse import unquote
    url = unquote(url)
    return quote(url, safe='/-_.')

if os.path.exists("notes"):
    shutil.rmtree("notes")

os.makedirs("notes", exist_ok=True)
for label in labels:
    note_files = set()
    os.makedirs(f"notes/{label}", exist_ok=True)
    

    for note in eval(label):
        filename = note.title
        if filename == "":
            filename = note.content
        filename = filename[:32]
        filename = sanitize_filename(filename)
        filename = get_unique_filename(filename, note_files)
        
        with open(f"notes/{label}/{filename}.md", "w") as f:
            if note.title != "":
                f.write("# " + note.title)
                if note.content != "":
                    f.write("\n\n")
            if note.content.count('\n') == 0 and note.content != "":
                f.write("# ")
            f.write(note.content)
            if note.attachments or note.annotations:
                f.write("\n\n")
            for attachment in note.attachments:
                if attachment.mimetype.startswith('image/'):
                    safe_path = encode_url(attachment.path)
                    safe_title = encode_markdown_text(attachment.path)
                    f.write(f"![{safe_title}]({safe_path})\n\n")
                else:
                    safe_path = encode_url(attachment.path)
                    safe_title = encode_markdown_text(f"{attachment.path} ({attachment.mimetype})")
                    f.write(f"Attachment: [{safe_title}]({safe_path})\n\n")
            
            for annotation in note.annotations:
                safe_url = encode_url(annotation.url)
                safe_title = encode_markdown_text(f"{annotation.description} ({annotation.source})")
                f.write(f"Annotation: [{safe_title}]({safe_url})\n\n")

    with open(f"notes/{label}.md", "w") as f:
        f.write(f"# {label}\n\n")
        
        note_files.clear()
        
        for note in eval(label):
            filename = note.title
            if filename == "":
                filename = note.content
            filename = filename[:32]
            filename = sanitize_filename(filename)
            filename = get_unique_filename(filename, note_files)
            
            safe_filename = encode_url(filename)
            safe_title = encode_markdown_text(filename)
            created_date = datetime.datetime.fromtimestamp(note.created_timestamp / 1_000_000).strftime('%Y-%m-%d')
            f.write(f"[{created_date} - {safe_title}]({label}/{safe_filename}.md)\n\n")

with open("notes/index.md", "w") as f:
    f.write("# INDEX\n\n")
    for label in labels:
        f.write(f"[{label}]({label}.md)\n\n")