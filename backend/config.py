import logging
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent / '.env')

logging.basicConfig(level=logging.INFO, format='%(levelname)s:     %(name)s - %(message)s')
logger = logging.getLogger('finsight')

# Render sets RENDER=true on every service; ENVIRONMENT=production works anywhere else.
IS_PRODUCTION = os.getenv('ENVIRONMENT', '').lower() == 'production' or bool(os.getenv('RENDER'))

SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    if IS_PRODUCTION:
        raise RuntimeError('SECRET_KEY must be set in production')
    SECRET_KEY = secrets.token_urlsafe(32)
    logger.warning('SECRET_KEY not set; using a random key for this run (tokens will not survive restarts)')

ALGORITHM = os.getenv('ALGORITHM', 'HS256')

FRONTEND_URL = os.getenv('FRONTEND_URL')
if not FRONTEND_URL:
    if IS_PRODUCTION:
        raise RuntimeError('FRONTEND_URL must be set in production')
    FRONTEND_URL = 'http://localhost:5173'
FRONTEND_URL = FRONTEND_URL.rstrip('/')

DEMO_EMAIL = 'demo@finsight.app'
DEMO_PASSWORD = 'demo1234'
