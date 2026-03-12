"""Entry point: python -m webdashboard"""
import uvicorn
from webdashboard.backend.main import app

uvicorn.run(app, host="0.0.0.0", port=8080)
