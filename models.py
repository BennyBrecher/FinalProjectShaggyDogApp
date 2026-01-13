from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin
from sqlalchemy import LargeBinary

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to generated images
    images = db.relationship('GeneratedImage', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.username}>'

class GeneratedImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    original_image_data = db.Column(LargeBinary, nullable=False)
    breed_detected = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(50), default='uploaded')  # uploaded, detecting, generating_1, generating_2, generating_final, completed, error
    error_message = db.Column(db.Text, nullable=True)  # Store detailed error messages
    image_1_data = db.Column(LargeBinary, nullable=True)  # First transition image
    image_2_data = db.Column(LargeBinary, nullable=True)  # Second transition image
    final_dog_image_data = db.Column(LargeBinary, nullable=True)  # Final dog image
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    batch_id = db.Column(db.String(50), nullable=True)  # Links paired records when pipeline_type is "both"
    pipeline_type = db.Column(db.String(20), nullable=True)  # Stores the pipeline type used: "dalle_gpt", "gpt_only", or "both"
    
    def get_progress_percent(self):
        """Calculate progress percentage based on status"""
        status_map = {
            'uploaded': 0,
            'detecting': 12.5,
            'generating_1': 37.5,
            'generating_2': 62.5,
            'generating_final': 87.5,
            'completed': 100,
            'error': 0
        }
        return status_map.get(self.status, 0)
    
    def __repr__(self):
        return f'<GeneratedImage {self.id} - User {self.user_id}>'
