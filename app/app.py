from flask import Flask, jsonify
import os
from datetime import datetime

app = Flask(__name__)

VERSION = os.getenv("APP_VERSION", "v1")
ENV_NAME = os.getenv("ENV_NAME", "production")

@app.route('/')
def home():
    return f"""
    <html>
    <body style="font-family: Arial; text-align: center; margin-top: 100px;">
        <h1>DevOps Pipeline with Automated Rollback</h1>
        <h2>Version: {VERSION}</h2>
        <p>Environment: {ENV_NAME}</p>
        <p>Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </body>
    </html>
    """

@app.route('/health')
def health():
    raise Exception("Intentional crash for rollback demo")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
