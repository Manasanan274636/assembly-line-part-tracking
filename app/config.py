import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    
    # Database Configuration for TiDB (MySQL Compatible)
    DB_USER = os.environ.get('DB_USER')
    DB_PASSWORD = os.environ.get('DB_PASSWORD')
    DB_HOST = os.environ.get('DB_HOST')
    DB_PORT = os.environ.get('DB_PORT')
    DB_NAME = os.environ.get('DB_NAME')
    
    # Construct URI if env vars are present, otherwise fallback to local sqlite for dev safety
    if DB_HOST and DB_USER:
        SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        # SSL options might be needed for TiDB Cloud
        if os.environ.get('DB_SSL_CA'):
             SQLALCHEMY_ENGINE_OPTIONS = {
                'connect_args': {
                    'ssl': {
                        'ca': os.environ.get('DB_SSL_CA')
                    }
                }
            }
    else:
        BASE_DIR = os.path.abspath(os.path.dirname(__file__))
        PROJECT_ROOT = os.path.dirname(BASE_DIR)
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(PROJECT_ROOT, 'assembly_line.db')

    SQLALCHEMY_TRACK_MODIFICATIONS = False
