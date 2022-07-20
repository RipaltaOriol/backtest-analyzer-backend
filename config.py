import os
from datetime import timedelta

class Config(object):
  # Uplodas directory
  UPLOAD_FOLDER = 'uploads'
  # Fonts directory
  FONTS_FOLDER = 'fonts'
  # Debug & Testing
  DEBUG = False
  # Session secret
  SESSION_TYPE = 'filesystem'
  # JWT secret
  JWT_SECRET_KEY = ';lakj343sdlkjf233@'

class ProductionConfig(Config):
  # Connect to the database
  MONGO_URI = 'mongodb+srv://appadmin0:backtestanalyzer@clusterbeta.xm49b.mongodb.net/backtest-analyzer?retryWrites=true&w=majority&ssl=true&ssl_cert_reqs=CERT_NONE'
  # JWT config
  JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
  pass

class DevelopmentConfig(Config):
  # Connect to the database
  MONGO_URI = 'mongodb://localhost/backtest-analyzer'
  # JWT config
  JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
  DEBUG = True

class TestingConfig(Config):
  TESTING = True