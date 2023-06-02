from app import app
from dotenv import load_dotenv

if __name__ == "__main__":
    # app.secret_key = 'secret-backtest-analyzer'
    debug = app.config["DEBUG"]

    app.run(debug=debug)
