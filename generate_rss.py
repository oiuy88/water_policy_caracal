import requests
from feedgen.feed import FeedGenerator
from dateutil import parser
import datetime

# Updated to the new Folder ID
ROOT_FOLDER_ID = "c0e2818a-febe-4af9-a75b-c00bd649f2ac"

# Updated to the new Group and Folder URL
FOLDER_URL = "https://circabc.europa.eu/ui/group/1c566741-ee2f-41e7-a915-7bd88bae7c03/library/c0e2818a-febe-4af9-a75b-c00bd649f2ac"

HEADERS = {
    "accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://circabc.europa.eu/"
}

def fetch_items(node_id, get_folders=False):
    folder_only = "true" if get_folders else "false"
    file_only = "false" if get_folders else "true"
    
    url = f"https://circabc.europa.eu/service/circabc/spaces/{node_id}/children?language=en&guest=true&limit=100&page=1&order=modified_DESC&folderOnly={folder_only}&fileOnly={file_only}&skipExpiredItems=true"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            return []
            
        data = response.json()
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            if 'data' in data:
                return data['data']
            if 'list' in data and 'entries' in data['list']:
                return [i.get('entry', i) for i in data['list']['entries']]
        return []
    except Exception:
        return []

def get_all_documents(node_id, depth=0, max_depth=5):
    if depth > max_depth:
        return []
        
    print(f"{'  ' * depth}Crawling folder ID: {node_id}...")
    documents = fetch_items(node_id, get_folders=False)
    subfolders = fetch_items(node_id, get_folders=True)
    
    for folder in subfolders:
        sub_id = folder.get('id')
        if sub_id:
            documents.extend(get_all_documents(sub_id, depth + 1, max_depth))
            
    return documents

def extract_meta(item, possible_keys):
    for k in possible_keys:
        if k in item and item[k]:
            return item[k]
    props = item.get('properties', {})
    for k in possible_keys:
        if k in props and props[k]:
            return props[k]
    return None

def build_rss():
    print("Starting recursive crawl of CIRCABC folders...")
    all_documents = get_all_documents(ROOT_FOLDER_ID)
    
    def get_date(doc):
        date_val = extract_meta(doc, ['modified', 'modifiedAt', 'modifiedOn', 'cm:modified', 'date'])
        try:
            return parser.parse(str(date_val))
        except:
            return datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
            
    all_documents.sort(key=get_date, reverse=True)
    latest_documents = all_documents[:50]
    
    fg = FeedGenerator()
    fg.title('CIRCABC Folder Updates')
    fg.link(href=FOLDER_URL, rel='alternate')
    fg.description('Latest document changes in the CIRCABC repository and subfolders')
    
    for item in latest_documents:
        fe = fg.add_entry()
        
        title = extract_meta(item, ['name', 'title', 'cm:name']) or 'Unknown Document'
        fe.title(title)
        
        node_id = item.get('id', '')
        
        # Updated to the new Group ID and appended /details to the end
        download_link = f"https://circabc.europa.eu/ui/group/1c566741-ee2f-41e7-a915-7bd88bae7c03/library/{node_id}/details"
        fe.link(href=download_link)
        fe.id(node_id)
        
        mime_type = extract_meta(item, ['mimeType', 'mimetype', 'cm:content.mimetype']) or 'Document'
        size = extract_meta(item, ['size', 'sizeInBytes', 'cm:content.size']) or 'Unknown size'
        author = extract_meta(item, ['modifier', 'modifiedBy', 'cm:modifier']) or 'System'
        
        fe.description(f"File: {title}<br>Type: {mime_type}<br>Size: {size}<br>Modified by: {author}")
        
        date_str = extract_meta(item, ['modified', 'modifiedAt', 'modifiedOn', 'cm:modified', 'date'])
        if date_str:
            try:
                dt = parser.parse(str(date_str))
                fe.published(dt)
                fe.updated(dt)
            except Exception:
                pass
                
    fg.rss_file('rss.xml')
    print("Successfully generated rss.xml")

if __name__ == '__main__':
    build_rss()
