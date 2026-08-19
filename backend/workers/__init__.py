"""Celery worker package.

Keep package initialization side-effect free. Import task modules explicitly in
worker processes so the web API never loads the embedding/ML stack at startup.
"""
