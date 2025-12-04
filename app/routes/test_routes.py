from flask import Blueprint, send_file, render_template_string
import os

test_bp = Blueprint("test", __name__, url_prefix="/test")

@test_bp.get("/google-oauth")
def test_google_oauth():
    """Serve test page untuk Google OAuth"""
    html_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        'test_google_login.html'
    )
    return send_file(html_path)

@test_bp.get("/")
def test_home():
    """Simple test home"""
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Bunda Care - Test Pages</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 600px;
                margin: 50px auto;
                padding: 20px;
            }
            h1 { color: #667eea; }
            ul { list-style: none; padding: 0; }
            li { margin: 10px 0; }
            a {
                display: block;
                padding: 15px 20px;
                background: #667eea;
                color: white;
                text-decoration: none;
                border-radius: 8px;
                transition: background 0.3s;
            }
            a:hover { background: #764ba2; }
        </style>
    </head>
    <body>
        <h1>🧪 Bunda Care Test Pages</h1>
        <ul>
            <li><a href="/test/google-oauth">🔐 Test Google OAuth</a></li>
            <li><a href="/api/auth/google" onclick="alert('Use POST method!'); return false;">📡 API Endpoint (POST only)</a></li>
        </ul>
    </body>
    </html>
    """)
