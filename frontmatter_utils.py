import yaml
import re
from datetime import datetime

def parse_frontmatter(content):
    """
    Parse YAML frontmatter from markdown content.
    Returns a tuple of (metadata dict, content without frontmatter)
    """
    if not content or not content.strip().startswith('---'):
        return {}, content
    
    # Match frontmatter pattern
    pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)$'
    match = re.match(pattern, content, re.DOTALL)
    
    if not match:
        return {}, content
    
    try:
        # Parse YAML frontmatter
        metadata = yaml.safe_load(match.group(1)) or {}
        content_body = match.group(2)
        return metadata, content_body
    except yaml.YAMLError:
        # If YAML parsing fails, return original content
        return {}, content

def create_frontmatter(metadata):
    """
    Create YAML frontmatter from metadata dict.
    """
    if not metadata:
        return ""
    
    # Filter out None values and empty strings
    filtered_metadata = {k: v for k, v in metadata.items() if v is not None and v != ''}
    
    if not filtered_metadata:
        return ""
    
    return f"---\n{yaml.dump(filtered_metadata, default_flow_style=False, sort_keys=False)}---\n\n"

def update_frontmatter(content, metadata):
    """
    Update or add frontmatter to content.
    """
    _, body = parse_frontmatter(content)
    frontmatter = create_frontmatter(metadata)
    return frontmatter + body

def extract_title_from_content(content):
    """
    Extract title from content, checking frontmatter first, then first line.
    """
    metadata, body = parse_frontmatter(content)
    
    # Check if title is in frontmatter
    if metadata.get('title'):
        return metadata['title']
    
    # Otherwise extract from first line of body
    lines = body.strip().split('\n')
    for line in lines:
        line = line.strip()
        if line:
            # Remove markdown headers if present
            return re.sub(r'^#+\s*', '', line)
    
    return 'Untitled Note'