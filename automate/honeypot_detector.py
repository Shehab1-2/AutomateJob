class HoneypotDetector:
    """Class to detect and skip honeypot/bot trap fields"""
    
    def __init__(self):
        # More specific honeypot keywords - removed common legitimate terms
        self.honeypot_keywords = [
            'beecatcher', 'honeypot', 'bot', 'trap', 'captcha',
            'robot', 'spam', 'hidden', 'invisible', 'fake',
            'security_check', 'bot_check'  # More specific security terms
        ]
        
        # Terms that are legitimate but might be confused as honeypots
        self.legitimate_keywords = [
            'verify', 'check', 'confirm', 'repeat', 'validation',
            'password', 'email', 'username', 'name', 'phone'
        ]
    
    async def is_honeypot_field(self, element):
        """Check if a field is a honeypot/bot trap field"""
        try:
            # Get element attributes
            automation_id = await element.get_attribute('data-automation-id') or ''
            name = await element.get_attribute('name') or ''
            _id = await element.get_attribute('id') or ''
            class_name = await element.get_attribute('class') or ''
            placeholder = await element.get_attribute('placeholder') or ''
            field_type = await element.get_attribute('type') or ''
            
            # Combine all attributes for checking
            all_attrs = f"{automation_id} {name} {_id} {class_name} {placeholder}".lower()
            
            # Special handling for password fields - be more lenient
            if field_type == 'password':
                # Only flag password fields as honeypots if they have very specific honeypot indicators
                strict_honeypot_keywords = ['beecatcher', 'honeypot', 'bot', 'trap', 'fake', 'spam']
                if any(keyword in all_attrs for keyword in strict_honeypot_keywords):
                    print(f"🚨 Password field flagged as honeypot: {all_attrs}")
                    return True
            else:
                # For non-password fields, use the full honeypot keyword list
                if any(keyword in all_attrs for keyword in self.honeypot_keywords):
                    # But first check if it contains legitimate keywords
                    has_legitimate = any(keyword in all_attrs for keyword in self.legitimate_keywords)
                    if has_legitimate:
                        print(f"🔍 Field has honeypot keywords but also legitimate ones: {all_attrs}")
                        # Only flag as honeypot if it has honeypot keywords AND is hidden
                    else:
                        print(f"🚨 Field flagged as honeypot by keywords: {all_attrs}")
                        return True
            
            # Check if field is hidden via CSS
            is_hidden = await element.evaluate('''
                element => {
                    const style = window.getComputedStyle(element);
                    return style.display === 'none' || 
                           style.visibility === 'hidden' || 
                           style.opacity === '0' ||
                           element.style.display === 'none' ||
                           element.style.visibility === 'hidden' ||
                           element.offsetHeight === 0 ||
                           element.offsetWidth === 0;
                }
            ''')
            
            if is_hidden:
                print(f"🚨 Field flagged as honeypot (hidden): {all_attrs}")
                return True
            
            # Check for suspicious positioning (off-screen)
            position = await element.evaluate('''
                element => {
                    const rect = element.getBoundingClientRect();
                    return {
                        left: rect.left,
                        top: rect.top,
                        width: rect.width,
                        height: rect.height
                    };
                }
            ''')
            
            # Field positioned way off screen or has zero dimensions
            if (position['left'] < -1000 or position['top'] < -1000 or 
                position['width'] == 0 or position['height'] == 0):
                print(f"🚨 Field flagged as honeypot (off-screen): {all_attrs}")
                return True
            
            # Additional check: if field has tabindex="-1" it might be a honeypot
            tabindex = await element.get_attribute('tabindex')
            if tabindex == '-1':
                print(f"🚨 Field flagged as honeypot (tabindex=-1): {all_attrs}")
                return True
                
            return False
            
        except Exception as e:
            print(f"❌ Error checking honeypot status: {e}")
            # If we can't determine, err on the side of caution and assume it's legitimate
            return False
    
    async def safe_fill_field(self, element, value, field_type="field"):
        """Safely fill a field after checking if it's a honeypot"""
        # Get field info for debugging
        try:
            name = await element.get_attribute('name') or 'unnamed'
            _id = await element.get_attribute('id') or 'no-id'
            field_input_type = await element.get_attribute('type') or 'text'
            print(f"🔍 Checking {field_type}: type='{field_input_type}', name='{name}', id='{_id}'")
        except:
            pass
        
        if await self.is_honeypot_field(element):
            print(f"⚠️  Skipping honeypot {field_type}")
            return False
        
        try:
            await element.fill(value)
            print(f"✅ Successfully filled {field_type}")
            return True
        except Exception as e:
            print(f"❌ Failed to fill {field_type}: {e}")
            return False
    
    async def safe_check_checkbox(self, element, field_type="checkbox"):
        """Safely check a checkbox after verifying it's not a honeypot"""
        # Get field info for debugging
        try:
            name = await element.get_attribute('name') or 'unnamed'
            _id = await element.get_attribute('id') or 'no-id'
            print(f"🔍 Checking {field_type}: name='{name}', id='{_id}'")
        except:
            pass
        
        if await self.is_honeypot_field(element):
            print(f"⚠️  Skipping honeypot {field_type}")
            return False
        
        try:
            if not await element.is_checked():
                await element.check()
            print(f"✅ Successfully checked {field_type}")
            return True
        except Exception as e:
            print(f"❌ Failed to check {field_type}: {e}")
            return False