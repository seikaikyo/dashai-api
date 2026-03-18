import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL', '')
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

CORS_ORIGINS = [
    'http://localhost:5173',
    'http://localhost:5174',
    'https://factory.dashai.dev',
    'https://smart-factory-demo.vercel.app',
    'https://smart-factory-demo-git-main-seikaikyos-projects.vercel.app',
    'https://smart-factory-demo-seikaikyos-projects.vercel.app',
]
