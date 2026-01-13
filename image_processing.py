import os
from openai import OpenAI
import requests
import random
from PIL import Image, ImageDraw
import io
import base64
import tempfile
import re
from dotenv import load_dotenv
from config import Config

# Ensure .env is loaded
load_dotenv()

# Dog breed characteristics mapping for detection
DOG_BREEDS = {
    'golden_retriever': {
        'features': ['friendly', 'blonde', 'long_hair', 'medium_size', 'kind_eyes'],
        'description': 'friendly and gentle Golden Retriever'
    },
    'labrador': {
        'features': ['friendly', 'short_hair', 'medium_size', 'athletic'],
        'description': 'friendly and energetic Labrador'
    },
    'german_shepherd': {
        'features': ['serious', 'pointed_ears', 'medium_hair', 'intelligent'],
        'description': 'intelligent and loyal German Shepherd'
    },
    'poodle': {
        'features': ['curly_hair', 'elegant', 'small_medium', 'refined'],
        'description': 'elegant and refined Poodle'
    },
    'bulldog': {
        'features': ['strong', 'short_hair', 'sturdy', 'wrinkled'],
        'description': 'strong and sturdy Bulldog'
    },
    'beagle': {
        'features': ['friendly', 'floppy_ears', 'medium_size', 'curious'],
        'description': 'friendly and curious Beagle'
    },
    'husky': {
        'features': ['striking_eyes', 'thick_coat', 'medium_large', 'wolf_like'],
        'description': 'striking and wolf-like Siberian Husky'
    },
    'dachshund': {
        'features': ['long_body', 'short_legs', 'small_medium', 'determined'],
        'description': 'determined and distinctive Dachshund'
    }
}

def detect_dog_breed(image_path):
    """
    Analyze the image using OpenAI's vision API to determine which dog breed the person most closely resembles.
    """
    try:
        # Get API key
        api_key = Config.OPENAI_API_KEY or os.environ.get('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set. Please check your .env file.")
        client = OpenAI(api_key=api_key)
        
        # Open and prepare image
        img = Image.open(image_path)
        
        # Convert to RGB if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Resize if image is too large (vision API has size limits)
        max_size = 2048
        if max(img.size) > max_size:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        # Convert image to base64
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        image_base64 = base64.b64encode(img_buffer.read()).decode('utf-8')
        
        # Create list of available breeds for the prompt
        breed_list = ', '.join([breed.replace('_', ' ').title() for breed in DOG_BREEDS.keys()])
        
        # Reframed prompt - focus on artistic/creative filter selection, avoid comparison language
        prompt_text = (
            f"This is a fun entertainment app that applies artistic dog-themed visual filters to photos, "
            f"similar to popular social media filters. Analyze this headshot photo and select which dog breed's "
            f"visual aesthetic style would best complement this photo for an artistic transformation effect. "
            f"Think of this like choosing a filter style - which breed's visual characteristics (color palette, "
            f"texture style, overall aesthetic) would create the most visually appealing artistic effect?\n\n"
            f"Available breed filter styles: {breed_list}\n\n"
            f"Respond with ONLY a JSON object in this exact format: {{\"breed\": \"labrador\"}}\n"
            f"Use one of these exact breed keys: golden_retriever, labrador, german_shepherd, poodle, "
            f"bulldog, beagle, husky, or dachshund. Use lowercase with underscores (e.g., \"golden_retriever\")."
        )
        
        # Try GPT-4o-mini first (may be less strict with content moderation)
        # If it fails, fall back to random selection
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",  # Using GPT-4o-mini which has vision capabilities and may be less strict
                messages=[
                    {
                        "role": "system",
                        "content": "You are a creative assistant for a fun entertainment app that applies artistic visual filters to photos, similar to Instagram filters or Snapchat lenses. This app applies dog-themed artistic effects for entertainment and creative purposes only. Your role is to help users select which visual filter style would create the most appealing artistic effect based on aesthetic compatibility, not to make comparisons. Analyze images and provide filter style selections as requested."
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt_text
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=100,
                temperature=0.3  # Lower temperature for more consistent responses
            )
        except Exception as mini_error:
            print(f"DEBUG: GPT-4o-mini failed, trying GPT-4o: {mini_error}")
            # Fallback to GPT-4o if mini fails
            response = client.chat.completions.create(
                model="gpt-4o",  # Fallback to GPT-4o
                messages=[
                    {
                        "role": "system",
                        "content": "You are a creative assistant for a fun entertainment app that applies artistic visual filters to photos, similar to Instagram filters or Snapchat lenses. This app applies dog-themed artistic effects for entertainment and creative purposes only. Your role is to help users select which visual filter style would create the most appealing artistic effect based on aesthetic compatibility, not to make comparisons. Analyze images and provide filter style selections as requested."
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt_text
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=100,
                temperature=0.3
            )
        
        # Extract breed from response
        raw_response = response.choices[0].message.content.strip()
        print(f"DEBUG: Raw GPT-4o breed detection response: {raw_response}")
        
        breed_response = raw_response.lower()
        
        # Comprehensive breed mapping - handle all variations
        breed_mapping = {
            # Golden Retriever variations
            'golden retriever': 'golden_retriever',
            'goldenretriever': 'golden_retriever',
            'golden_retriever': 'golden_retriever',
            # Labrador variations
            'labrador': 'labrador',
            'labrador retriever': 'labrador',
            'labradorretriever': 'labrador',
            # German Shepherd variations
            'german shepherd': 'german_shepherd',
            'germanshepherd': 'german_shepherd',
            'german_shepherd': 'german_shepherd',
            'alsatian': 'german_shepherd',  # Alternative name
            # Poodle variations
            'poodle': 'poodle',
            # Bulldog variations
            'bulldog': 'bulldog',
            'english bulldog': 'bulldog',
            'englishbulldog': 'bulldog',
            # Beagle variations
            'beagle': 'beagle',
            # Husky variations
            'husky': 'husky',
            'siberian husky': 'husky',
            'siberianhusky': 'husky',
            # Dachshund variations
            'dachshund': 'dachshund',
            'wiener dog': 'dachshund',
            'wienerdog': 'dachshund',
            'sausage dog': 'dachshund',
            'sausagedog': 'dachshund'
        }
        
        selected_breed = None
        
        # Try to parse JSON first
        try:
            import json
            # Try to find JSON object in response
            json_match = re.search(r'\{[^}]*"breed"\s*:\s*"([^"]+)"[^}]*\}', breed_response)
            if json_match:
                json_breed = json_match.group(1).strip().lower()
                print(f"DEBUG: Extracted breed from JSON: {json_breed}")
                # Map the JSON breed value
                if json_breed in DOG_BREEDS:
                    selected_breed = json_breed
                elif json_breed in breed_mapping:
                    selected_breed = breed_mapping[json_breed]
        except Exception as json_error:
            print(f"DEBUG: JSON parsing failed: {json_error}")
        
        # If JSON parsing didn't work, try direct key matching
        if not selected_breed:
            for key in DOG_BREEDS.keys():
                # Check for exact key match (with underscores or spaces)
                pattern = r'\b' + re.escape(key) + r'\b'
                if re.search(pattern, breed_response):
                    selected_breed = key
                    print(f"DEBUG: Found direct key match: {key}")
                    break
                # Also check with spaces instead of underscores
                key_with_spaces = key.replace('_', ' ')
                pattern_spaces = r'\b' + re.escape(key_with_spaces) + r'\b'
                if re.search(pattern_spaces, breed_response, re.IGNORECASE):
                    selected_breed = key
                    print(f"DEBUG: Found key match with spaces: {key}")
                    break
        
        # Try comprehensive mapping if direct match didn't work
        if not selected_breed:
            for variant, key in breed_mapping.items():
                # Use word boundaries to avoid partial matches
                pattern = r'\b' + re.escape(variant) + r'\b'
                if re.search(pattern, breed_response, re.IGNORECASE):
                    selected_breed = key
                    print(f"DEBUG: Found breed via mapping: {variant} -> {key}")
                    break
        
        # Fallback to random breed if no match found or if API refused (but log it)
        if not selected_breed:
            if "sorry" in breed_response.lower() or "can't help" in breed_response.lower():
                print(f"WARNING: API refused the request. Raw response: {raw_response}")
                print(f"WARNING: Falling back to random breed selection due to API refusal.")
                # Random selection from available breeds
                selected_breed = random.choice(list(DOG_BREEDS.keys()))
                print(f"WARNING: Selected random breed: {selected_breed}")
            else:
                print(f"WARNING: Could not parse breed from response. Raw response: {raw_response}")
                print(f"WARNING: Lowercase response: {breed_response}")
                print(f"WARNING: Defaulting to golden_retriever. This may indicate a parsing issue.")
                selected_breed = 'golden_retriever'
        else:
            print(f"DEBUG: Successfully detected breed: {selected_breed}")
        
        return selected_breed, DOG_BREEDS[selected_breed]['description']
        
    except Exception as e:
        print(f"ERROR: Error detecting breed with vision API: {e}")
        import traceback
        print(f"ERROR: Traceback: {traceback.format_exc()}")
        # Fallback to default
        print(f"ERROR: Falling back to golden_retriever due to error")
        return 'golden_retriever', DOG_BREEDS['golden_retriever']['description']

def create_face_mask(target_size, face_region_size=None, face_top_offset=None):
    """
    Create a face mask - transparent (editable) on face area, opaque (preserved) elsewhere
    Returns the mask as a PIL Image
    """
    if face_region_size is None:
        face_region_size = int(target_size * 0.5)  # 50% of image size
    if face_top_offset is None:
        face_top_offset = int(target_size * 0.2)  # Start a bit below top
    
    mask = Image.new('RGBA', (target_size, target_size), (0, 0, 0, 255))  # Start with fully opaque (black)
    draw = ImageDraw.Draw(mask)
    
    # Calculate facial region
    face_left = (target_size - face_region_size) // 2
    face_top = face_top_offset
    face_right = face_left + face_region_size
    face_bottom = face_top + face_region_size
    
    # Draw transparent ellipse for the facial region (transparent = editable)
    draw.ellipse([face_left, face_top, face_right, face_bottom], fill=(255, 255, 255, 0))
    
    return mask

def create_safe_radius_mask(target_size, face_region_size=None, face_top_offset=None, safe_radius_percent=0.60):
    """
    Create a "donut" mask with safe radius border around face
    - Face area (inner circle): Opaque (preserved)
    - Safe radius border (donut ring): Transparent (editable) - for adding ears/fur
    - Background (outer area): Opaque (preserved)
    Returns the mask as a PIL Image
    Increased safe_radius_percent to 0.60 (60%) to provide much more space for ears and fur
    """
    if face_region_size is None:
        face_region_size = int(target_size * 0.5)  # 50% of image size
    if face_top_offset is None:
        face_top_offset = int(target_size * 0.2)  # Start a bit below top
    
    # Start with fully opaque (everything preserved)
    mask = Image.new('RGBA', (target_size, target_size), (0, 0, 0, 255))
    draw = ImageDraw.Draw(mask)
    
    # Calculate inner face ellipse (will remain opaque/preserved)
    face_left = (target_size - face_region_size) // 2
    face_top = face_top_offset
    face_right = face_left + face_region_size
    face_bottom = face_top + face_region_size
    
    # Calculate outer border ellipse (this ring will be transparent/editable)
    # safe_radius_percent determines how much larger the outer ellipse is (e.g., 0.60 = 60% larger)
    # Increased to 60% to provide much more space for ears (top sides) and fur (around head outline)
    border_expansion = int(face_region_size * safe_radius_percent)
    border_left = face_left - border_expansion
    border_top = face_top - border_expansion
    border_right = face_right + border_expansion
    border_bottom = face_bottom + border_expansion
    
    # Draw outer ellipse (transparent = editable border area)
    draw.ellipse([border_left, border_top, border_right, border_bottom], fill=(255, 255, 255, 0))
    
    # Draw inner ellipse (opaque = preserved face area) to create the donut
    draw.ellipse([face_left, face_top, face_right, face_bottom], fill=(0, 0, 0, 255))
    
    return mask

def create_full_head_mask(target_size, head_region_size=None, head_top_offset=None):
    """
    Create a full head mask - transparent (editable) on full head area, opaque (preserved) elsewhere
    Covers: face area (where snout is) + top of head (where ears are) + hair/head outline
    Returns the mask as a PIL Image
    """
    if head_region_size is None:
        head_region_size = int(target_size * 0.65)  # 65% of image size (larger than face to cover full head)
    if head_top_offset is None:
        head_top_offset = int(target_size * 0.05)  # Start closer to top to cover ears
    
    mask = Image.new('RGBA', (target_size, target_size), (0, 0, 0, 255))  # Start with fully opaque (black)
    draw = ImageDraw.Draw(mask)
    
    # Calculate full head region (larger ellipse covering face + ears + head outline)
    head_left = (target_size - head_region_size) // 2
    head_top = head_top_offset
    head_right = head_left + head_region_size
    head_bottom = head_top + head_region_size
    
    # Draw transparent ellipse for the full head region (transparent = editable)
    draw.ellipse([head_left, head_top, head_right, head_bottom], fill=(255, 255, 255, 0))
    
    return mask

def create_head_and_body_mask(target_size, head_region_size=None, head_top_offset=None):
    """
    Create a mask covering head + upper body/torso area - transparent (editable) on head+body, opaque (preserved) elsewhere
    Covers: head area + upper body/torso (shoulders, chest, where clothing is visible)
    Returns the mask as a PIL Image
    """
    if head_region_size is None:
        head_region_size = int(target_size * 0.65)  # 65% of image size for head
    if head_top_offset is None:
        head_top_offset = int(target_size * 0.05)  # Start closer to top to cover ears
    
    mask = Image.new('RGBA', (target_size, target_size), (0, 0, 0, 255))  # Start with fully opaque (black)
    draw = ImageDraw.Draw(mask)
    
    # Calculate head region
    head_left = (target_size - head_region_size) // 2
    head_top = head_top_offset
    head_right = head_left + head_region_size
    head_bottom = head_top + head_region_size
    
    # Calculate body region (extends below head, covers upper torso)
    # Body starts below head and extends down to cover shoulders/chest area
    body_width = int(target_size * 0.75)  # Body is wider than head
    body_left = (target_size - body_width) // 2
    body_top = head_bottom - int(head_region_size * 0.2)  # Overlap slightly with head
    body_bottom = int(target_size * 0.75)  # Cover upper body/torso area
    body_right = body_left + body_width
    
    # Draw transparent ellipse for head region (transparent = editable)
    draw.ellipse([head_left, head_top, head_right, head_bottom], fill=(255, 255, 255, 0))
    
    # Draw transparent ellipse for body region (transparent = editable)
    draw.ellipse([body_left, body_top, body_right, body_bottom], fill=(255, 255, 255, 0))
    
    return mask

def ensure_png_under_4mb(image_path, max_size_mb=3.5):
    """
    Ensure PNG file is under 4MB by resizing if needed.
    Uses 3.5MB as threshold to leave safety margin.
    Modifies the file in place if necessary.
    Returns the actual size used (1024 or 512) for API size parameter.
    """
    max_size_bytes = max_size_mb * 1024 * 1024
    
    # Check current file size
    current_size = os.path.getsize(image_path)
    if current_size <= max_size_bytes:
        return 1024  # Original size is fine
    
    # File is too large, need to resize
    print(f"Warning: PNG file is {current_size / (1024*1024):.2f}MB, resizing to 512x512...")
    
    img = Image.open(image_path)
    
    # Resize to 512x512 (should be well under 4MB)
    img_resized = img.resize((512, 512), Image.Resampling.LANCZOS)
    
    # Save with optimization
    img_resized.save(image_path, format='PNG', optimize=True)
    
    new_size = os.path.getsize(image_path)
    print(f"Resized to 512x512, new size: {new_size / (1024*1024):.2f}MB")
    return 512

def edit_image_with_dalle(original_image_path, edit_prompt, size="1024x1024", mask_type="face", face_mask=None):
    """
    Edit an image using OpenAI DALL-E 2 image editing API
    Note: DALL-E 3 doesn't support editing, so we use DALL-E 2's edit endpoint
    
    Args:
        original_image_path: Path to the image to edit
        edit_prompt: The editing prompt
        size: Target size (e.g., "1024x1024")
        mask_type: "face" (face area editable), "inverted" (face preserved, everything else editable), 
                   "safe_radius" (donut mask - only border around face editable)
        face_mask: Optional pre-generated face mask (PIL Image). If None, will be generated.
    """
    try:
        # Try to get API key from Config, fallback to environment variable
        api_key = Config.OPENAI_API_KEY or os.environ.get('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set. Please check your .env file.")
        client = OpenAI(api_key=api_key)
        
        # Open and prepare the image
        img = Image.open(original_image_path)
        
        # Convert to RGB if needed (RGBA will be handled)
        if img.mode == 'RGBA':
            # Create a white background
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])  # Use alpha channel as mask
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Make image square and resize to target size (required by edit API)
        # Edit API supports 256x256, 512x512, 1024x1024 and requires PNG < 4MB
        target_size = int(size.split('x')[0])
        
        # First, resize to target size to ensure file size is manageable
        width, height = img.size
        if width != height:
            # Make square by cropping/resizing to the larger dimension first
            size_dim = max(width, height)
            # Resize to square, then resize to target size
            img = img.resize((size_dim, size_dim), Image.Resampling.LANCZOS)
        
        # Resize to target size (1024x1024 should be under 4MB when saved as PNG)
        if img.size[0] != target_size:
            img = img.resize((target_size, target_size), Image.Resampling.LANCZOS)
        
        # Save image to temporary file as PNG (required by API)
        img_temp_fd, img_temp_path = tempfile.mkstemp(suffix='.png')
        mask_temp_path = None
        try:
            os.close(img_temp_fd)
            # Save as PNG with optimization to keep file size under 4MB
            img.save(img_temp_path, format='PNG', optimize=True)
            
            # Ensure file is under 4MB before sending to API (may resize to 512x512)
            actual_size = ensure_png_under_4mb(img_temp_path)
            api_size = f"{actual_size}x{actual_size}"
            
            # If image was resized, we need to reload it and recreate masks at the new size
            if actual_size != target_size:
                img = Image.open(img_temp_path)
                target_size = actual_size
            
            # Create mask based on mask_type
            # Transparent areas = editable, Opaque/black areas = preserved
            if face_mask is None:
                face_mask = create_face_mask(target_size)
            
            if mask_type == "safe_radius":
                # Safe radius mask: "donut" shape - only border around face is editable
                # Face area and background are preserved, only the border ring is editable
                mask = create_safe_radius_mask(target_size)
            elif mask_type == "inverted":
                # Inverted mask: face area is opaque (preserved), everything else is transparent (editable)
                # This allows adding features around the face without editing the face itself
                mask = Image.new('RGBA', (target_size, target_size), (255, 255, 255, 0))  # Start with fully transparent
                # Draw opaque ellipse on face area to preserve it (invert the face_mask logic)
                draw = ImageDraw.Draw(mask)
                # Use same face region calculation as create_face_mask
                face_region_size = int(target_size * 0.5)
                face_left = (target_size - face_region_size) // 2
                face_top = int(target_size * 0.2)
                face_right = face_left + face_region_size
                face_bottom = face_top + face_region_size
                # Draw opaque ellipse (black with full alpha) to preserve face area
                draw.ellipse([face_left, face_top, face_right, face_bottom], fill=(0, 0, 0, 255))
            else:  # mask_type == "face"
                # Face mask: face area is transparent (editable), everything else is opaque (preserved)
                mask = face_mask
            
            mask_temp_fd, mask_temp_path = tempfile.mkstemp(suffix='.png')
            os.close(mask_temp_fd)
            mask.save(mask_temp_path, format='PNG')
            
            # Open files in binary read mode for the API
            with open(img_temp_path, 'rb') as img_file, open(mask_temp_path, 'rb') as mask_file:
                # Call the edit endpoint (DALL-E 2 editing API)
                response = client.images.edit(
                    image=img_file,
                    mask=mask_file,
                    prompt=edit_prompt,
                    n=1,
                    size=api_size
                )
            
            image_url = response.data[0].url
            
            # Download the edited image
            img_response = requests.get(image_url)
            img_response.raise_for_status()
            
            return img_response.content
            
        except Exception as edit_error:
            # If editing fails (e.g., DALL-E 2 endpoint not available), raise with helpful message
            error_msg = str(edit_error)
            if "edit" in error_msg.lower() or "not found" in error_msg.lower():
                raise ValueError(
                    f"Image editing API may not be available. "
                    f"DALL-E 3 doesn't support image editing. "
                    f"Original error: {error_msg}"
                )
            raise
        finally:
            # Clean up temporary files
            try:
                if mask_temp_path and os.path.exists(mask_temp_path):
                    os.unlink(mask_temp_path)
            except:
                pass
            try:
                if os.path.exists(img_temp_path):
                    os.unlink(img_temp_path)
            except:
                pass
        
    except Exception as e:
        print(f"Error editing image: {e}")
        raise

def edit_image_with_gpt_image1(original_image_path, edit_prompt, size="1024x1024", mask_type="face", face_mask=None):
    """
    Edit an image using OpenAI gpt-image-1 image editing API
    
    Args:
        original_image_path: Path to the image to edit
        edit_prompt: The editing prompt
        size: Target size (e.g., "1024x1024")
        mask_type: "face" (face area editable), "safe_radius" (donut mask - only border around face editable)
        face_mask: Optional pre-generated face mask (PIL Image). If None, will be generated.
    """
    try:
        api_key = Config.OPENAI_API_KEY or os.environ.get('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set. Please check your .env file.")
        client = OpenAI(api_key=api_key)
        
        # Open and prepare the image
        img = Image.open(original_image_path)
        
        # Convert to RGB if needed
        if img.mode == 'RGBA':
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Make image square and resize to target size (required by edit API)
        target_size = int(size.split('x')[0])
        
        # First, resize to target size to ensure file size is manageable
        width, height = img.size
        if width != height:
            size_dim = max(width, height)
            img = img.resize((size_dim, size_dim), Image.Resampling.LANCZOS)
        
        if img.size[0] != target_size:
            img = img.resize((target_size, target_size), Image.Resampling.LANCZOS)
        
        # Save image to temporary file as PNG (required by API)
        img_temp_fd, img_temp_path = tempfile.mkstemp(suffix='.png')
        mask_temp_path = None
        try:
            os.close(img_temp_fd)
            img.save(img_temp_path, format='PNG', optimize=True)
            
            # Ensure file is under 4MB before sending to API (may resize to 512x512)
            actual_size = ensure_png_under_4mb(img_temp_path)
            api_size = f"{actual_size}x{actual_size}"
            
            # If image was resized, we need to reload it and recreate masks at the new size
            if actual_size != target_size:
                img = Image.open(img_temp_path)
                target_size = actual_size
            
            # Create mask based on mask_type
            # Transparent areas = editable, Opaque/black areas = preserved
            if face_mask is None:
                face_mask = create_face_mask(target_size)
            
            if mask_type == "safe_radius":
                # Safe radius mask: "donut" shape - only border around face is editable
                mask = create_safe_radius_mask(target_size)
            else:  # mask_type == "face"
                # Face mask: face area is transparent (editable), everything else is opaque (preserved)
                mask = face_mask
            
            mask_temp_fd, mask_temp_path = tempfile.mkstemp(suffix='.png')
            os.close(mask_temp_fd)
            mask.save(mask_temp_path, format='PNG')
            
            # Open files in binary read mode for the API
            with open(img_temp_path, 'rb') as img_file, open(mask_temp_path, 'rb') as mask_file:
                # Call the edit endpoint (gpt-image-1 editing API)
                response = client.images.edit(
                    model="gpt-image-1",
                    image=img_file,
                    mask=mask_file,
                    prompt=edit_prompt,
                    n=1,
                    size=api_size
                )
            
            if not hasattr(response, 'data') or not response.data or len(response.data) == 0:
                raise ValueError(f"API response missing or empty 'data' attribute. Response: {response}")
            
            data_item = response.data[0]
            
            # gpt-image-1 edit API may return URL or b64_json format
            if hasattr(data_item, 'url') and data_item.url:
                image_url = data_item.url
                img_response = requests.get(image_url)
                img_response.raise_for_status()
                return img_response.content
            elif hasattr(data_item, 'b64_json') and data_item.b64_json:
                image_data = base64.b64decode(data_item.b64_json)
                return image_data
            else:
                raise ValueError(f"API response data[0] has neither 'url' nor 'b64_json'. Data item: {data_item}, Attributes: {dir(data_item)}")
            
        except Exception as edit_error:
            error_msg = str(edit_error)
            print(f"Error in gpt-image-1 edit API: {error_msg}")
            raise
        finally:
            # Clean up temporary files
            try:
                if mask_temp_path and os.path.exists(mask_temp_path):
                    os.unlink(mask_temp_path)
            except:
                pass
            try:
                if os.path.exists(img_temp_path):
                    os.unlink(img_temp_path)
            except:
                pass
        
    except Exception as e:
        print(f"Error editing image with gpt-image-1: {e}")
        raise

def finalize_with_gpt_image1_enhance_only(stage2_image_path, breed_name_display, breed_features=None):
    """
    Finalize the human-dog hybrid transformation using OpenAI's gpt-image-1 edit API (enhancement-only, no body fur)
    This stage enhances the quality and improves fur texture/details on the head while preserving structure
    
    Args:
        stage2_image_path: Path to the Stage 2 output image (with ears and snout)
        breed_name_display: Display name of the breed
        breed_features: Optional list of breed features for prompt customization
    Returns:
        Image data (bytes)
    """
    try:
        api_key = Config.OPENAI_API_KEY or os.environ.get('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set. Please check your .env file.")
        client = OpenAI(api_key=api_key)
        
        # Build breed-specific description for the prompt
        breed_desc = breed_name_display
        if breed_features:
            if 'long_hair' in breed_features:
                breed_desc += " with long, shaggy fur"
            elif 'curly_hair' in breed_features:
                breed_desc += " with curly, shaggy fur"
            elif 'thick_coat' in breed_features:
                breed_desc += " with thick, shaggy fur"
        
        # Create prompt focused on enhancing existing transformation (head only, no body fur)
        prompt = f"Enhance the existing anthropomorphic human-dog hybrid transformation. Improve the fur texture, details, and quality of the {breed_name_display} dog features (ears and snout) on the head while keeping the exact same structure, composition, and background. Enhance the realism and quality of the dog fur and textures on the head without changing the overall appearance or layout. Keep the background exactly the same."
        
        # Open and prepare the Stage 2 image
        img = Image.open(stage2_image_path)
        
        # Convert to RGB if needed
        if img.mode == 'RGBA':
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Make image square and resize to 1024x1024 (required by edit API)
        target_size = 1024
        width, height = img.size
        if width != height:
            size_dim = max(width, height)
            img = img.resize((size_dim, size_dim), Image.Resampling.LANCZOS)
        
        if img.size[0] != target_size:
            img = img.resize((target_size, target_size), Image.Resampling.LANCZOS)
        
        # Save image to temporary file as PNG (required by API)
        img_temp_fd, img_temp_path = tempfile.mkstemp(suffix='.png')
        mask_temp_path = None
        try:
            os.close(img_temp_fd)
            img.save(img_temp_path, format='PNG', optimize=True)
            
            # Ensure file is under 4MB before sending to API (may resize to 512x512)
            actual_size = ensure_png_under_4mb(img_temp_path)
            api_size = f"{actual_size}x{actual_size}"
            
            # If image was resized, we need to reload it and recreate masks at the new size
            if actual_size != target_size:
                img = Image.open(img_temp_path)
                target_size = actual_size
            
            # Create full head mask (covers face + ears + head outline, no body)
            mask = create_full_head_mask(target_size)
            
            mask_temp_fd, mask_temp_path = tempfile.mkstemp(suffix='.png')
            os.close(mask_temp_fd)
            mask.save(mask_temp_path, format='PNG')
            
            # Use gpt-image-1 edit API to enhance the image
            print(f"DEBUG: Calling gpt-image-1 edit API (enhance-only) with prompt length: {len(prompt)}")
            with open(img_temp_path, 'rb') as img_file, open(mask_temp_path, 'rb') as mask_file:
                response = client.images.edit(
                    model="gpt-image-1",
                    image=img_file,
                    mask=mask_file,
                    prompt=prompt,
                    n=1,
                    size=api_size
                )
            
            print(f"DEBUG: API call succeeded. Response type: {type(response)}")
            
            if not hasattr(response, 'data') or not response.data or len(response.data) == 0:
                raise ValueError(f"API response missing or empty 'data' attribute. Response: {response}")
            
            data_item = response.data[0]
            print(f"DEBUG: Response data item type: {type(data_item)}")
            print(f"DEBUG: Response data item attributes: {dir(data_item)}")
            
            # gpt-image-1 edit API returns URL format by default
            if hasattr(data_item, 'url') and data_item.url:
                print(f"DEBUG: Using URL format")
                image_url = data_item.url
                print(f"DEBUG: Image URL from API: {image_url}")
                img_response = requests.get(image_url)
                img_response.raise_for_status()
                print(f"DEBUG: Successfully downloaded image from URL, size: {len(img_response.content)} bytes")
                return img_response.content
            elif hasattr(data_item, 'b64_json') and data_item.b64_json:
                print(f"DEBUG: Using b64_json format (base64-encoded image)")
                image_data = base64.b64decode(data_item.b64_json)
                print(f"DEBUG: Successfully decoded base64 image, size: {len(image_data)} bytes")
                return image_data
            else:
                raise ValueError(f"API response data[0] has neither 'url' nor 'b64_json'. Data item: {data_item}, Attributes: {dir(data_item)}")
            
        except Exception as edit_error:
            error_msg = str(edit_error)
            print(f"Error in gpt-image-1 edit API (enhance-only): {error_msg}")
            raise
        finally:
            # Clean up temporary files
            try:
                if mask_temp_path and os.path.exists(mask_temp_path):
                    os.unlink(mask_temp_path)
            except:
                pass
            try:
                if os.path.exists(img_temp_path):
                    os.unlink(img_temp_path)
            except:
                pass
        
    except Exception as e:
        print(f"Error finalizing with gpt-image-1 (enhance-only): {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        raise

def finalize_with_gpt_image1(stage2_image_path, breed_name_display, breed_features=None):
    """
    Finalize the human-dog hybrid transformation using OpenAI's gpt-image-1 edit API
    This stage enhances the quality and improves fur texture/details while preserving structure
    
    Args:
        stage2_image_path: Path to the Stage 2 output image (with ears and snout)
        breed_name_display: Display name of the breed
        breed_features: Optional list of breed features for prompt customization
    Returns:
        Image data (bytes)
    """
    try:
        api_key = Config.OPENAI_API_KEY or os.environ.get('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set. Please check your .env file.")
        client = OpenAI(api_key=api_key)
        
        # Build breed-specific description for the prompt
        breed_desc = breed_name_display
        if breed_features:
            if 'long_hair' in breed_features:
                breed_desc += " with long, shaggy fur"
            elif 'curly_hair' in breed_features:
                breed_desc += " with curly, shaggy fur"
            elif 'thick_coat' in breed_features:
                breed_desc += " with thick, shaggy fur"
        
        # Create prompt focused on enhancing transformation and adding body fur
        prompt = f"Enhance the existing anthropomorphic human-dog hybrid transformation. Improve the fur texture, details, and quality of the {breed_name_display} dog features (ears and snout) on the head. Additionally, add fluffy, fuzzy, furry {breed_name_display} dog fur to the body, torso, and shoulders - make the body area covered in soft, shaggy dog fur while preserving the clothing underneath. Enhance the realism and quality of the dog fur and textures on both the head and body. Keep the exact same structure, composition, and background. Keep the background exactly the same."
        
        # Open and prepare the Stage 2 image
        img = Image.open(stage2_image_path)
        
        # Convert to RGB if needed
        if img.mode == 'RGBA':
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Make image square and resize to 1024x1024 (required by edit API)
        target_size = 1024
        width, height = img.size
        if width != height:
            size_dim = max(width, height)
            img = img.resize((size_dim, size_dim), Image.Resampling.LANCZOS)
        
        if img.size[0] != target_size:
            img = img.resize((target_size, target_size), Image.Resampling.LANCZOS)
        
        # Save image to temporary file as PNG (required by API)
        img_temp_fd, img_temp_path = tempfile.mkstemp(suffix='.png')
        mask_temp_path = None
        try:
            os.close(img_temp_fd)
            img.save(img_temp_path, format='PNG', optimize=True)
            
            # Ensure file is under 4MB before sending to API (may resize to 512x512)
            actual_size = ensure_png_under_4mb(img_temp_path)
            api_size = f"{actual_size}x{actual_size}"
            
            # If image was resized, we need to reload it and recreate masks at the new size
            if actual_size != target_size:
                img = Image.open(img_temp_path)
                target_size = actual_size
            
            # Create head and body mask (covers face + ears + head outline + upper body/torso)
            mask = create_head_and_body_mask(target_size)
            
            mask_temp_fd, mask_temp_path = tempfile.mkstemp(suffix='.png')
            os.close(mask_temp_fd)
            mask.save(mask_temp_path, format='PNG')
            
            # Use gpt-image-1 edit API to enhance the image
            print(f"DEBUG: Calling gpt-image-1 edit API with prompt length: {len(prompt)}")
            with open(img_temp_path, 'rb') as img_file, open(mask_temp_path, 'rb') as mask_file:
                response = client.images.edit(
                    model="gpt-image-1",
                    image=img_file,
                    mask=mask_file,
                    prompt=prompt,
                    n=1,
                    size=api_size
                )
            
            print(f"DEBUG: API call succeeded. Response type: {type(response)}")
            
            if not hasattr(response, 'data') or not response.data or len(response.data) == 0:
                raise ValueError(f"API response missing or empty 'data' attribute. Response: {response}")
            
            data_item = response.data[0]
            print(f"DEBUG: Response data item type: {type(data_item)}")
            print(f"DEBUG: Response data item attributes: {dir(data_item)}")
            
            # gpt-image-1 edit API returns URL format by default
            if hasattr(data_item, 'url') and data_item.url:
                print(f"DEBUG: Using URL format")
                image_url = data_item.url
                print(f"DEBUG: Image URL from API: {image_url}")
                img_response = requests.get(image_url)
                img_response.raise_for_status()
                print(f"DEBUG: Successfully downloaded image from URL, size: {len(img_response.content)} bytes")
                return img_response.content
            elif hasattr(data_item, 'b64_json') and data_item.b64_json:
                print(f"DEBUG: Using b64_json format (base64-encoded image)")
                image_data = base64.b64decode(data_item.b64_json)
                print(f"DEBUG: Successfully decoded base64 image, size: {len(image_data)} bytes")
                return image_data
            else:
                raise ValueError(f"API response data[0] has neither 'url' nor 'b64_json'. Data item: {data_item}, Attributes: {dir(data_item)}")
            
        except Exception as edit_error:
            error_msg = str(edit_error)
            print(f"Error in gpt-image-1 edit API: {error_msg}")
            raise
        finally:
            # Clean up temporary files
            try:
                if mask_temp_path and os.path.exists(mask_temp_path):
                    os.unlink(mask_temp_path)
            except:
                pass
            try:
                if os.path.exists(img_temp_path):
                    os.unlink(img_temp_path)
            except:
                pass
        
    except Exception as e:
        print(f"Error finalizing with gpt-image-1: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        raise

def generate_transformation_images(original_image_path, breed_description, image_id, breed_name=None, pipeline_type="gpt_only"):
    """
    Generate 2 transition images and 1 final dog image
    
    Pipeline types:
    - "dalle_gpt": DALL-E 2 for Stages 1-2, gpt-image-1 for Stage 3 (enhance-only, no body fur)
    - "gpt_only": gpt-image-1 for all stages (Stage 3 adds body fur)
    
    Returns binary data dict with keys: 'image_1', 'image_2', 'final'
    """
    
    # Get breed-specific features if breed_name is provided
    breed_features = []
    breed_traits = ""
    if breed_name and breed_name in DOG_BREEDS:
        breed_features = DOG_BREEDS[breed_name].get('features', [])
        # Extract visual traits that can be used in prompts
        visual_traits = []
        if 'pointed_ears' in breed_features:
            visual_traits.append('pointed ears')
        if 'floppy_ears' in breed_features:
            visual_traits.append('floppy ears')
        if 'striking_eyes' in breed_features:
            visual_traits.append('striking eyes')
        if 'wrinkled' in breed_features:
            visual_traits.append('wrinkled facial features')
        if 'curly_hair' in breed_features:
            visual_traits.append('curly texture')
        if 'thick_coat' in breed_features:
            visual_traits.append('thicker coat texture')
        if 'long_hair' in breed_features:
            visual_traits.append('longer hair texture')
        if 'short_hair' in breed_features:
            visual_traits.append('shorter, smoother texture')
        if visual_traits:
            breed_traits = ", ".join(visual_traits)
    
    breed_name_display = breed_description.replace('dog', '').strip() if not breed_name else breed_name.replace('_', ' ').title()
    
    # Create face mask from original image for reference (used in stage 3)
    # Read original image to get size
    original_img = Image.open(original_image_path)
    if original_img.mode != 'RGB':
        original_img = original_img.convert('RGB')
    width, height = original_img.size
    size_dim = max(width, height)
    if size_dim != 1024:
        size_dim = 1024
    
    face_mask = create_face_mask(1024)  # Create face mask at target size
    
    # Edit prompts to ADD dog features incrementally
    # Pipeline: Original → (add ears around face border) → Transition 1 → (add snout in face) → Transition 2 → (finalize with gpt-image-1) → Final
    # Stage 1: Use gpt-image-1 edit API with safe_radius mask (face and background preserved, only border around face editable)
    # Stage 2: Use gpt-image-1 edit API with face mask (background preserved, only face editable)
    # Stage 3: Use gpt-image-1 edit API with full_head mask (finalize/upscale)
    
    # Stage 1: ONLY add dog ears AROUND/OUTSIDE the face border (face and background untouched)
    ear_description = ""
    if breed_features:
        if 'pointed_ears' in breed_features:
            ear_description = "pointed"
        elif 'floppy_ears' in breed_features:
            ear_description = "floppy"
    ear_type = f"{ear_description} " if ear_description else ""
    
    prompt_1 = f"Add two large, authentic {ear_type}{breed_name_display} dog ears with dog ear texture and fur, one on each side of the top of the head. The ears should be clearly visible and prominent, positioned symmetrically on opposite sides at the top of the head, outside the face area. The ears must have dog ear texture - fur-covered, canine appearance, not human ear texture. Make the ears realistic and breed-appropriate with proper dog ear material and texture. CRITICAL: DO NOT change or edit the face itself - the face must remain COMPLETELY UNCHANGED. Keep all facial features exactly as they are - do not modify the eyes, nose, mouth, skin, or any part of the face. The face should look identical to the original. Do not change the background - keep the background exactly as it is. Do not add any other dogs, dog faces, or dog heads into the image. Only add the two dog ears at the top sides of the head. Transform the person by adding dog ears, do not add a separate dog next to the person."
    
    # Stage 2: ONLY add dog snout WITHIN the face area (background preserved, using original face mask reference)
    prompt_2 = f"Add a {breed_name_display} dog snout/nose to the face area. Only modify the nose/snout region within the face. Do not change the background - keep the background exactly as it is. Keep the eyes, facial structure, and all features outside the face exactly as they are. Keep ALL previous edits: the dog ears from the previous stage must remain visible and unchanged."
    
    images = {}
    temp_img_1_path = None
    temp_img_2_path = None
    
    try:
        # Stage 1: Edit first transition image from original - use safe_radius mask (add ears around face border, preserve background)
        try:
            print(f"Editing Stage 1 (adding ears around face border, preserving background) using {pipeline_type} pipeline...")
            if pipeline_type == "dalle_gpt":
                img_1_data = edit_image_with_dalle(original_image_path, prompt_1, mask_type="safe_radius", face_mask=face_mask)
            else:  # gpt_only
                img_1_data = edit_image_with_gpt_image1(original_image_path, prompt_1, mask_type="safe_radius", face_mask=face_mask)
            images['image_1'] = img_1_data
            
            # Write Stage 1 to temp file for Stage 2 processing (API functions need file paths)
            temp_img_1_fd, temp_img_1_path = tempfile.mkstemp(suffix='.png')
            os.close(temp_img_1_fd)
            with open(temp_img_1_path, 'wb') as f:
                f.write(img_1_data)
        except Exception as e:
            error_msg = str(e)
            print(f"Error in Stage 1 (adding ears): {error_msg}")
            raise ValueError(f"Stage 1 Error (adding ears): {error_msg}") from e
        
        # Stage 2: Edit second transition image from the first transition - use face mask (add snout in face, preserve background)
        try:
            print(f"Editing Stage 2 (adding snout in face, preserving background) using {pipeline_type} pipeline...")
            if pipeline_type == "dalle_gpt":
                img_2_data = edit_image_with_dalle(temp_img_1_path, prompt_2, mask_type="face", face_mask=face_mask)
            else:  # gpt_only
                img_2_data = edit_image_with_gpt_image1(temp_img_1_path, prompt_2, mask_type="face", face_mask=face_mask)
            images['image_2'] = img_2_data
            
            # Write Stage 2 to temp file for Stage 3 processing
            temp_img_2_fd, temp_img_2_path = tempfile.mkstemp(suffix='.png')
            os.close(temp_img_2_fd)
            with open(temp_img_2_path, 'wb') as f:
                f.write(img_2_data)
        except Exception as e:
            error_msg = str(e)
            print(f"Error in Stage 2 (adding snout): {error_msg}")
            raise ValueError(f"Stage 2 Error (adding snout): {error_msg}") from e
        
        # Stage 3: Finalize using gpt-image-1 (upscale quality, improve fur, enhance overall appearance)
        try:
            print(f"Finalizing Stage 3 with gpt-image-1 using {pipeline_type} pipeline...")
            if pipeline_type == "dalle_gpt":
                img_final_data = finalize_with_gpt_image1_enhance_only(temp_img_2_path, breed_name_display, breed_features)
            else:  # gpt_only
                img_final_data = finalize_with_gpt_image1(temp_img_2_path, breed_name_display, breed_features)
            images['final'] = img_final_data
        except Exception as e:
            error_msg = str(e)
            print(f"Error in Stage 3 (finalizing with gpt-image-1): {error_msg}")
            raise ValueError(f"Stage 3 Error (finalizing with gpt-image-1): {error_msg}") from e
        
    except Exception as e:
        # Re-raise with stage context (already includes stage info if it came from above)
        raise
    finally:
        # Clean up temporary files
        if temp_img_1_path and os.path.exists(temp_img_1_path):
            try:
                os.unlink(temp_img_1_path)
            except:
                pass
        if temp_img_2_path and os.path.exists(temp_img_2_path):
            try:
                os.unlink(temp_img_2_path)
            except:
                pass
    
    return images

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS
