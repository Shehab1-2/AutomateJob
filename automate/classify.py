import re
from bs4 import BeautifulSoup

def classify_field(tag, label_text=""):
    """Classify a form field based on its attributes and label"""
    attrs = tag.attrs
    name = attrs.get('name', '').lower()
    _id = attrs.get('id', '').lower()
    _type = attrs.get('type', '').lower()
    placeholder = attrs.get('placeholder', '').lower()
    automation_id = attrs.get('data-automation-id', '').lower()
    
    # Combine all text for pattern matching
    all_text = f"{name} {_id} {_type} {placeholder} {automation_id} {label_text}".lower()
    
    # Email field
    if 'email' in all_text or _type == 'email':
        return 'email'
    
    # Password fields
    if 'password' in all_text or _type == 'password':
        if 'confirm' in all_text or 'repeat' in all_text:
            return 'confirm_password'
        return 'password'
    
    # Checkboxes
    if _type == 'checkbox':
        if 'terms' in all_text or 'conditions' in all_text or 'agree' in all_text:
            return 'terms_checkbox'
        if 'privacy' in all_text or 'policy' in all_text:
            return 'privacy_checkbox'
        return 'checkbox'
    
    # Common text fields
    if 'first' in all_text and 'name' in all_text:
        return 'first_name'
    if 'last' in all_text and 'name' in all_text:
        return 'last_name'
    if 'phone' in all_text or _type == 'tel':
        return 'phone'
    
    # Dropdowns
    if tag.name == 'select':
        return 'dropdown'
    
    # Generic text input
    if _type in ['text', ''] and tag.name == 'input':
        return 'text_input'
    
    return 'unknown'

def is_required(tag, field_type):
    """Check if a field is required"""
    attrs = tag.attrs
    
    # Terms checkboxes are always required for signup
    if field_type == 'terms_checkbox':
        return True
    
    return (attrs.get('required') is not None or 
            attrs.get('aria-required') == 'true' or
            'required' in attrs.get('class', []))

def build_selector(tag):
    """Build a CSS selector for the field"""
    attrs = tag.attrs
    
    # Prefer data-automation-id
    if 'data-automation-id' in attrs:
        return f'{tag.name}[data-automation-id="{attrs["data-automation-id"]}"]'
    
    # Then id
    if 'id' in attrs:
        return f'{tag.name}[id="{attrs["id"]}"]'
    
    # Then name
    if 'name' in attrs:
        return f'{tag.name}[name="{attrs["name"]}"]'
    
    # Then type
    if 'type' in attrs:
        return f'{tag.name}[type="{attrs["type"]}"]'
    
    return f'{tag.name}'

def analyze_form_fields(html):
    """Analyze HTML and return actionable field information"""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Map labels to their inputs
    label_map = {}
    for label in soup.find_all('label'):
        if label.get('for'):
            label_map[label['for']] = label.get_text(strip=True)
    
    # Find all form fields
    fields = []
    for tag in soup.find_all(['input', 'select', 'textarea']):
        # Skip hidden fields
        if tag.get('type') == 'hidden':
            continue
        
        label_text = label_map.get(tag.get('id', ''), '')
        field_type = classify_field(tag, label_text)
        required = is_required(tag, field_type)
        selector = build_selector(tag)
        
        fields.append({
            'type': field_type,
            'selector': selector,
            'required': required,
            'label': label_text,
            'tag': tag.name
        })
    
    return fields

def print_actionable_fields(fields):
    """Print fields that need action in a clean format"""
    
    # Define what needs action
    actionable_types = {
        'email': '✉️  Email',
        'password': '🔒 Password',
        'confirm_password': '🔒 Confirm Password',
        'terms_checkbox': '☑️  Terms Checkbox',
        'privacy_checkbox': '☑️  Privacy Checkbox',
        'first_name': '📝 First Name',
        'last_name': '📝 Last Name',
        'phone': '📞 Phone',
        'dropdown': '📋 Dropdown',
        'checkbox': '☑️  Checkbox',
        'text_input': '📝 Text Input'
    }
    
    print("\n📋 FIELDS TO FILL:")
    print("=" * 50)
    
    actionable_fields = [f for f in fields if f['type'] in actionable_types]
    
    if not actionable_fields:
        print("❌ No actionable fields found")
        return
    
    for field in actionable_fields:
        icon = actionable_types.get(field['type'], '📝')
        required_text = " (REQUIRED)" if field['required'] else " (OPTIONAL)"
        label_text = f" - {field['label']}" if field['label'] else ""
        
        print(f"{icon}: {field['selector']}{required_text}{label_text}")

# Example usage - integrate this with your existing code
def main():
    # Read the HTML file your script created
    try:
        with open("page_dump.html", "r", encoding="utf-8") as f:
            html = f.read()
        
        fields = analyze_form_fields(html)
        print_actionable_fields(fields)
        
    except FileNotFoundError:
        print("❌ page_dump.html not found. Run your HTML fetcher first.")

if __name__ == "__main__":
    main()