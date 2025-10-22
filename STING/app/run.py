# run.py
import os
import sys
from flask import Flask
from app import create_app

port = int(os.environ.get('APP_PORT', 5050))
app = create_app()

# Get the Flask app from middleware
flask_app = app.app if hasattr(app, 'app') else app

ssl_context = None
# Check multiple possible certificate locations
cert_locations = [
    ('/app/certs/server.crt', '/app/certs/server.key'),
    (os.path.expanduser('~/.sting/certs/server.crt'), os.path.expanduser('~/.sting/certs/server.key'))
]

for cert_path, key_path in cert_locations:
    if os.path.exists(cert_path) and os.path.exists(key_path):
        ssl_context = (cert_path, key_path)
        print(f"Using SSL certificates from: {cert_path}")
        break

if __name__ == '__main__':
    if os.environ.get('FLASK_ENV') == 'production':
        from gunicorn.app.base import BaseApplication

        class GunicornApp(BaseApplication):
            def __init__(self, app, options=None):
                self.options = options or {}
                self.application = app
                super().__init__()

            def load_config(self):
                for key, value in self.options.items():
                    self.cfg.set(key, value)
                    
            def load(self):
                return self.application

        options = {
            'bind': f'0.0.0.0:{port}',
            'workers': 4,
            'timeout': 120
        }
        
        if ssl_context:
            options.update({
                'certfile': ssl_context[0],
                'keyfile': ssl_context[1]
            })
            
        GunicornApp(flask_app, options).run()
    else:
        flask_app.run(
            host='0.0.0.0',
            port=port,
            debug=True,
            ssl_context=ssl_context
        )