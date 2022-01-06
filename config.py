import os
from datetime import timedelta

class Config(object):
  # Connect to the database
  MONGO_URI = 'mongodb://localhost/backtest-analyzer'
  # Uplodas directory
  UPLOAD_FOLDER = 'uploads'
  # Debug & Testing
  DEBUG = False
  DEBUG = False
  # Session secret
  SESSION_TYPE = 'filesystem'
  # JWT secret
  JWT_SECRET_KEY = ';lakj343sdlkjf233@'

class ProductionConfig(Config):
  pass

class DevelopmentConfig(Config):
  JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
  DEBUG = True

class TestingConfig(Config):
  TESTING = True