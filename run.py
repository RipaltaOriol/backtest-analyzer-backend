from app import app
from dotenv import load_dotenv

if __name__ == "__main__":
    # app.secret_key = 'secret-backtest-analyzer'
    # from werkzeug.middleware.profiler import ProfilerMiddleware
    # app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=("FilterController.py"), profile_dir="./profile")
    debug = app.config["DEBUG"]

    app.run(debug=debug)
