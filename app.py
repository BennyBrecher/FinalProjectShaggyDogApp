from flask import Flask, render_template, request, redirect, url_for, flash, Response
from flask_login import LoginManager, login_required, current_user
from werkzeug.utils import secure_filename
import os
import threading
import tempfile
from datetime import datetime

from config import Config
from models import db, User, GeneratedImage
from auth import auth_bp
from image_processing import detect_dog_breed, generate_transformation_images, allowed_file

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('auth.login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Display user's generated images"""
    user_images = GeneratedImage.query.filter_by(user_id=current_user.id).order_by(GeneratedImage.created_at.asc()).all()
    
    # Group images by batch_id for paired displays
    paired_images = {}
    single_images = []
    
    for image in user_images:
        if image.batch_id:
            if image.batch_id not in paired_images:
                paired_images[image.batch_id] = []
            paired_images[image.batch_id].append(image)
        else:
            single_images.append(image)
    
    # Create paired_list and calculate sequence numbers
    paired_list = []
    for batch_id, images in paired_images.items():
        if len(images) == 2:
            # Sort the pair so dalle_gpt comes first
            images.sort(key=lambda x: x.pipeline_type or '')
            paired_list.append({
                'batch_id': batch_id,
                'image_1': images[0],  # dalle_gpt
                'image_2': images[1],  # gpt_only
                'created_at': images[0].created_at  # Use first image's timestamp for sorting
            })
        else:
            # If only one image in pair (edge case), treat as single
            single_images.extend(images)
    
    # Create unified list with all items (paired + single) for display
    unified_items = []
    
    # Add paired items with type marker
    for pair in paired_list:
        unified_items.append({
            'type': 'paired',
            'data': pair,
            'created_at': pair['created_at']
        })
    
    # Add single items with type marker
    for image in single_images:
        unified_items.append({
            'type': 'single',
            'data': image,
            'created_at': image.created_at
        })
    
    # Sort unified list by creation date (newest first)
    unified_items.sort(key=lambda x: x['created_at'], reverse=True)
    
    # Calculate per-user sequence numbers (1 = oldest, N = newest)
    # But we display newest first, so we'll reverse the sequence number calculation
    total_count = len(unified_items)
    sequence_map = {}  # Maps (image_id or batch_id) to sequence number
    
    for idx, item in enumerate(unified_items):
        seq_num = total_count - idx  # Reverse: newest gets highest number
        if item['type'] == 'paired':
            batch_id = item['data']['batch_id']
            sequence_map[batch_id] = seq_num
        else:
            image_id = item['data'].id
            sequence_map[image_id] = seq_num
    
    return render_template('dashboard.html', unified_items=unified_items, sequence_map=sequence_map)

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    """Handle image upload and initiate transformation"""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            # Read file into memory as binary data
            file_data = file.read()
            
            # Get pipeline type from form (default to "gpt_only" if not provided)
            pipeline_type = request.form.get('pipeline_type', 'gpt_only')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Handle "both" pipeline type - create two records and launch two threads
            if pipeline_type == 'both':
                # Generate a batch_id to link the two records
                batch_id = f"{current_user.id}_{timestamp}"
                
                # Create first database entry (DALL-E 2 + gpt-image-1)
                new_image_1 = GeneratedImage(
                    user_id=current_user.id,
                    original_image_data=file_data,
                    breed_detected=None,
                    status='uploaded',
                    batch_id=batch_id,
                    pipeline_type='dalle_gpt'
                )
                db.session.add(new_image_1)
                
                # Create second database entry (All gpt-image-1)
                new_image_2 = GeneratedImage(
                    user_id=current_user.id,
                    original_image_data=file_data,
                    breed_detected=None,
                    status='uploaded',
                    batch_id=batch_id,
                    pipeline_type='gpt_only'
                )
                db.session.add(new_image_2)
                db.session.commit()
                
                # Start both image generations in separate threads
                thread1 = threading.Thread(
                    target=process_image_generation,
                    args=(new_image_1.id, 'dalle_gpt')
                )
                thread1.daemon = True
                thread1.start()
                
                thread2 = threading.Thread(
                    target=process_image_generation,
                    args=(new_image_2.id, 'gpt_only')
                )
                thread2.daemon = True
                thread2.start()
                
                flash('Image uploaded! Both pipelines running simultaneously.', 'success')
            else:
                # Single pipeline - create one database entry
                new_image = GeneratedImage(
                    user_id=current_user.id,
                    original_image_data=file_data,
                    breed_detected=None,
                    status='uploaded',
                    pipeline_type=pipeline_type
                )
                db.session.add(new_image)
                db.session.commit()
                
                # Start image generation in a thread
                thread = threading.Thread(
                    target=process_image_generation,
                    args=(new_image.id, pipeline_type)
                )
                thread.daemon = True
                thread.start()
                
                flash('Image uploaded! Generation in progress.', 'success')
            
            # Redirect to dashboard to show progress (which auto-refreshes)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid file type. Please upload an image (png, jpg, jpeg, gif, webp)', 'error')
    
    return render_template('upload.html')

def process_image_generation(image_id, pipeline_type="gpt_only"):
    """Process image generation in a background thread"""
    from models import GeneratedImage as GIImage
    temp_original_path = None
    try:
        with app.app_context():
            image_record = GIImage.query.get(image_id)
            if not image_record:
                return
            
            # Write original image to temporary file for processing (API functions need file paths)
            temp_original_fd, temp_original_path = tempfile.mkstemp(suffix='.png')
            os.close(temp_original_fd)
            with open(temp_original_path, 'wb') as f:
                f.write(image_record.original_image_data)
            
            # Update status: detecting breed
            image_record.status = 'detecting'
            db.session.commit()
            
            # Detect breed
            breed, breed_description = detect_dog_breed(temp_original_path)
            image_record.breed_detected = breed
            image_record.status = 'generating_1'
            db.session.commit()
            
            # Generate transformation images - returns binary data dict
            generated_images = generate_transformation_images(temp_original_path, breed_description, image_id, breed_name=breed, pipeline_type=pipeline_type)
            
            # Update database with generated image binary data
            image_record.image_1_data = generated_images['image_1']
            image_record.status = 'generating_2'
            db.session.commit()
            
            image_record.image_2_data = generated_images['image_2']
            image_record.status = 'generating_final'
            db.session.commit()
            
            image_record.final_dog_image_data = generated_images['final']
            image_record.status = 'completed'
            db.session.commit()
            
    except Exception as e:
        import traceback
        error_msg = str(e)
        error_traceback = traceback.format_exc()
        print(f"Error processing image generation: {error_msg}")
        print(f"Traceback: {error_traceback}")
        with app.app_context():
            image_record = GIImage.query.get(image_id)
            if image_record:
                image_record.status = 'error'
                image_record.error_message = f"Error: {error_msg}"
                db.session.commit()
    finally:
        # Clean up temporary file
        if temp_original_path and os.path.exists(temp_original_path):
            try:
                os.unlink(temp_original_path)
            except:
                pass

@app.route('/image/<int:image_id>/<image_type>')
@login_required
def serve_image(image_id, image_type):
    """Serve images from database"""
    image_record = GeneratedImage.query.get_or_404(image_id)
    
    # Verify ownership
    if image_record.user_id != current_user.id:
        flash('Unauthorized access', 'error')
        return redirect(url_for('dashboard'))
    
    # Get image data based on type
    image_data = None
    if image_type == 'original':
        image_data = image_record.original_image_data
    elif image_type == 'transition1':
        image_data = image_record.image_1_data
    elif image_type == 'transition2':
        image_data = image_record.image_2_data
    elif image_type == 'final':
        image_data = image_record.final_dog_image_data
    else:
        flash('Invalid image type', 'error')
        return redirect(url_for('dashboard'))
    
    if not image_data:
        flash('Image not found', 'error')
        return redirect(url_for('dashboard'))
    
    # Determine content type (default to PNG)
    content_type = 'image/png'
    
    return Response(image_data, mimetype=content_type)

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

# Create database tables
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
