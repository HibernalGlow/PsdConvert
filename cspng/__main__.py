"""
CSPNG包主入口点

支持通过 python -m cspng 运行。
"""

from .cli.main import app

if __name__ == "__main__":
    app()
