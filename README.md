# Shaggy Dog Web App

A Flask-based web application that transforms human headshots into dog versions using AI. The app uses OpenAI's DALL-E 2 and GPT-4o Vision APIs to detect which dog breed a person most resembles, then progressively transforms the image through multiple stages to create an anthropomorphic dog version.

## Features

### Core Functionality
- **User Authentication**: Secure user registration and login with encrypted password storage
- **Image Upload**: Upload headshot photos (PNG, JPG, JPEG, GIF, WEBP, max 16MB)
- **Dog Breed Detection**: Uses GPT-4o Vision API to automatically detect which dog breed the person most closely resembles
- **Multi-Stage Image Transformation**: 
  - Stage 1: Adds authentic dog ears around the head
  - Stage 2: Adds dog snout to the face
  - Stage 3: Finalizes and enhances the transformation quality
- **Dual Pipeline Options**:
  - **Pipeline A (DALL-E 2 + gpt-image-1)**: Stages 1-2 use DALL-E 2, Stage 3 uses gpt-image-1 for head-only enhancement
  - **Pipeline B (All gpt-image-1)**: All stages use gpt-image-1, with Stage 3 adding body fur
  - **Pipeline C (Multithreaded Both)**: Runs both pipelines simultaneously and displays results side-by-side for comparison
- **Real-time Progress Tracking**: Visual progress indicators with progress bars and step-by-step status messages
- **Dashboard**: View all your generated transformations with per-user sequential numbering
- **Image Storage**: All uploaded and generated images are securely stored per user

### Technical Features
- **Multithreading**: Background image processing using Python's threading module
- **Automatic PNG Optimization**: Images are automatically resized/compressed to meet API requirements (4MB limit)
- **Error Handling**: Comprehensive error handling with user-friendly error messages
- **Responsive Design**: Modern, clean UI with mobile-responsive design
- **Auto-login**: Users are automatically logged in after registration

## Tech Stack

- **Backend**: Python 3.x, Flask
- **Database**: PostgreSQL with SQLAlchemy ORM (images stored as BLOBs)
- **Authentication**: Flask-Login with Werkzeug password hashing
- **Image Processing**: PIL/Pillow for image manipulation
- **AI APIs**: 
  - OpenAI GPT-4o Vision API (breed detection)
  - OpenAI DALL-E 2 API (image editing, Stages 1-2 in Pipeline A)
  - OpenAI gpt-image-1 API (image editing, Stage 3 in Pipeline A, all stages in Pipeline B)
- **Frontend**: HTML5, CSS3, JavaScript (vanilla)

## Installation

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file in the project root:
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   SECRET_KEY=your_secret_key_here
   DATABASE_URL=postgresql://user:password@localhost/dbname
   ```
   For local development, you can use SQLite by setting:
   ```env
   DATABASE_URL=sqlite:///shaggydog.db
   ```
5. Run the application:
   ```bash
   python app.py
   ```
6. Navigate to `http://127.0.0.1:5000` in your browser

## Project Structure

```
FinalProjectShaggyDogWebApp/
├── app.py                 # Main Flask application
├── auth.py                # Authentication routes (register, login, logout)
├── models.py              # Database models (User, GeneratedImage)
├── image_processing.py    # Image processing functions (breed detection, transformations)
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (not in git)
├── README.md              # This file
├── static/
│   ├── css/
│   │   └── style.css     # Application styles
│   └── js/
│       ├── dashboard.js  # Dashboard auto-refresh logic
│       └── upload.js     # Image preview on upload page
└── templates/
    ├── base.html         # Base template
    ├── dashboard.html    # User dashboard (displays transformations)
    ├── upload.html       # Image upload page
    ├── login.html        # Login page
    └── register.html     # Registration page
```

**Note**: All images are stored as BLOBs in the database. The `uploads/` directory has been removed - no filesystem storage is needed.

## Usage

1. **Register/Login**: Create an account or log in to an existing one
2. **Upload Image**: Navigate to the upload page and select a headshot photo
3. **Choose Pipeline**: Select your preferred transformation pipeline:
   - DALL-E 2 + gpt-image-1 (head-only enhancement)
   - All gpt-image-1 (adds body fur)
   - Launch Both Generation Routes Via Multithreading (runs both simultaneously)
4. **Monitor Progress**: The dashboard automatically refreshes to show progress with visual indicators
5. **View Results**: Once complete, view your transformation with all three stages displayed

## Image Transformation Pipeline

### Stage 1: Adding Dog Ears
- Adds breed-appropriate dog ears to the top/sides of the head
- Uses a "safe radius" mask to preserve the face while adding ears around it
- Face remains completely unchanged

### Stage 2: Adding Dog Snout
- Transforms the face area to add a dog snout
- Builds on Stage 1's results (ears are preserved)
- Uses face mask for precise editing

### Stage 3: Finalization
- **Pipeline A**: Enhances head quality and fur texture (head only)
- **Pipeline B**: Enhances head quality and adds fluffy fur to the body/torso
- Improves overall realism and quality of the transformation

## Database Schema

### User Model
- `id`: Primary key
- `username`: Unique username
- `password_hash`: Encrypted password
- `created_at`: Account creation timestamp

### GeneratedImage Model
- `id`: Primary key
- `user_id`: Foreign key to User
- `original_image_data`: Binary data (BLOB) of uploaded image
- `breed_detected`: Detected dog breed (e.g., "golden_retriever")
- `status`: Processing status (uploaded, detecting, generating_1, generating_2, generating_final, completed, error)
- `error_message`: Error details if processing fails
- `image_1_data`: Binary data (BLOB) of Stage 1 output (ears added)
- `image_2_data`: Binary data (BLOB) of Stage 2 output (snout added)
- `final_dog_image_data`: Binary data (BLOB) of Stage 3 output (finalized)
- `created_at`: Creation timestamp
- `batch_id`: Links paired records for multithreaded "both" option
- `pipeline_type`: Pipeline used (dalle_gpt, gpt_only, or null)

## Recent Updates

### Latest Improvements
- **PostgreSQL Migration**: Migrated from SQLite to PostgreSQL for production deployment
- **BLOB Storage**: All images (uploaded and generated) are now stored as BLOBs in the database instead of filesystem, enabling deployment on platforms with ephemeral filesystems (e.g., Render)
- **Improved Radio Button UI**: Enhanced styling with better visual feedback and hover states
- **Multithreaded Pipeline Option**: Added ability to run both pipelines simultaneously for side-by-side comparison
- **PNG Size Validation**: Automatic image compression/resizing (to 512x512 if needed) to prevent 4MB API errors, with dynamic API size parameter adjustment
- **Fixed Display Order**: Dashboard now shows newest transformations first, properly sorting both single and paired results
- **Per-User Transformation Numbers**: Each user's transformations are numbered sequentially (1, 2, 3...) instead of using global database IDs
- **Auto-login After Registration**: Users are automatically logged in after successful account creation
- **Enhanced Breed Detection**: 
  - Improved parsing logic with comprehensive breed mapping and debug logging
  - Added system message to frame as creative entertainment application to avoid content moderation refusals
  - Updated prompt to use "would work best for creative transformation" phrasing

## API Requirements

- OpenAI API key with access to:
  - GPT-4o (for breed detection)
  - DALL-E 2 (for Pipeline A stages 1-2)
  - gpt-image-1 (for Pipeline A stage 3 and Pipeline B all stages)

## Deployment (Render)

This application is designed for deployment on Render or similar platforms:

1. **Database Setup**: 
   - Create a PostgreSQL database on Render (free tier available)
   - Render automatically provides `DATABASE_URL` environment variable
   - No code changes needed - the app reads `DATABASE_URL` from environment

2. **Environment Variables** (set in Render dashboard):
   - `DATABASE_URL`: Automatically provided by Render PostgreSQL add-on
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `SECRET_KEY`: A secure random string for Flask sessions

3. **Image Storage**:
   - All images are stored as BLOBs in PostgreSQL
   - No filesystem storage required (works with Render's ephemeral filesystem)
   - Images are served directly from the database via `/image/<id>/<type>` route
   - The `uploads/` directory has been removed from the project - all image data is stored in the database

4. **Build Command**: `pip install -r requirements.txt`
5. **Start Command**: `python app.py` (or `gunicorn app:app` for production)

## Notes

- Image processing runs in background threads to avoid blocking the web interface
- All images (uploaded and generated) are stored as BLOBs in the database - no filesystem storage needed
- The `uploads/` directory has been removed - all image data is stored in the database
- Each transformation takes approximately 2-3 minutes to complete
- The application automatically handles image format conversion and optimization
- Images are automatically resized to 512x512 if they exceed 3.5MB to meet API requirements
- Breed detection uses a system message to clarify this is a creative/entertainment application
- For local development, SQLite can be used by setting `DATABASE_URL=sqlite:///shaggydog.db`

## License

This project is for educational/demonstration purposes.