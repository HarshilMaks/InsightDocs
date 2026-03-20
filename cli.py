"""Command-line interface for InsightDocs."""
import click
import requests
import json
from pathlib import Path
import os


API_BASE_URL = "http://localhost:8000/api/v1"
TOKEN_FILE = Path.home() / ".insightdocs_token"


def get_headers():
    """Get headers with authentication token if available."""
    if TOKEN_FILE.exists():
        token = TOKEN_FILE.read_text().strip()
        return {"Authorization": f"Bearer {token}"}
    return {}


@click.group()
def cli():
    """InsightDocs CLI - Manage documents and queries."""
    pass


@cli.command()
@click.option('--email', prompt=True, help='User email')
@click.option('--password', prompt=True, hide_input=True, help='User password')
def login(email, password):
    """Login to get an authentication token."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/auth/login",
            data={"username": email, "password": password}  # OAuth2 expects form data
        )
        if response.status_code == 200:
            token = response.json().get("access_token")
            TOKEN_FILE.write_text(token)
            click.echo("✓ Login successful! Token saved.")
        else:
            click.echo(f"✗ Login failed: {response.text}", err=True)
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)


@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
def upload(file_path):
    """Upload a document for processing."""
    headers = get_headers()
    if not headers:
        click.echo("✗ Not logged in. Run 'python cli.py login' first.", err=True)
        return

    click.echo(f"Uploading {file_path}...")
    
    with open(file_path, 'rb') as f:
        files = {'file': (Path(file_path).name, f)}
        response = requests.post(f"{API_BASE_URL}/documents/upload", files=files, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        click.echo(f"✓ Document uploaded successfully!")
        click.echo(f"  Document ID: {data['document_id']}")
        click.echo(f"  Task ID: {data['task_id']}")
    elif response.status_code == 401:
        click.echo("✗ Unauthorized. Please login again.", err=True)
    else:
        click.echo(f"✗ Upload failed: {response.text}", err=True)


@cli.command()
@click.argument('query_text')
@click.option('--top-k', default=5, help='Number of results to retrieve')
def query(query_text, top_k):
    """Query documents using natural language."""
    headers = get_headers()
    if not headers:
        click.echo("✗ Not logged in. Run 'python cli.py login' first.", err=True)
        return

    click.echo(f"Processing query: {query_text}")
    
    payload = {
        "query": query_text,
        "top_k": top_k
    }
    response = requests.post(f"{API_BASE_URL}/query/", json=payload, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        click.echo("\n" + "="*60)
        click.echo("ANSWER:")
        click.echo("="*60)
        click.echo(data['answer'])
        click.echo("\n" + "="*60)
        click.echo(f"SOURCES ({len(data['sources'])} found):")
        click.echo("="*60)
        for i, source in enumerate(data['sources'], 1):
            click.echo(f"\n[{i}] (distance: {source.get('distance', 0):.4f})")
            content = source.get('text', '') or source.get('content_preview', '')
            click.echo(content[:200] + "..." if len(content) > 200 else content)
    elif response.status_code == 401:
        click.echo("✗ Unauthorized. Please login again.", err=True)
    else:
        click.echo(f"✗ Query failed: {response.text}", err=True)


@cli.command()
def list_documents():
    """List all documents."""
    headers = get_headers()
    if not headers:
        click.echo("✗ Not logged in. Run 'python cli.py login' first.", err=True)
        return

    response = requests.get(f"{API_BASE_URL}/documents/", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        click.echo(f"\nFound {data['total']} document(s):\n")
        for doc in data['documents']:
            click.echo(f"ID: {doc['id']}")
            click.echo(f"  Filename: {doc['filename']}")
            click.echo(f"  Status: {doc['status']}")
            click.echo(f"  Created: {doc['created_at']}")
            click.echo()
    elif response.status_code == 401:
        click.echo("✗ Unauthorized. Please login again.", err=True)
    else:
        click.echo(f"✗ Failed to list documents: {response.text}", err=True)


@cli.command()
@click.argument('task_id')
def status(task_id):
    """Check status of a task."""
    headers = get_headers()
    # Note: Status check might be public depending on implementation, but safer to include auth
    # If unauth is allowed for task status, we can relax this. Assuming auth required.
    
    response = requests.get(f"{API_BASE_URL}/tasks/{task_id}", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        click.echo(f"\nTask Status: {data['status']}")
        click.echo(f"Progress: {data['progress']:.1f}%")
        if data.get('error'):
            click.echo(f"Error: {data['error']}")
        if data.get('result'):
            click.echo(f"\nResult:")
            click.echo(json.dumps(data['result'], indent=2))
    elif response.status_code == 401:
        click.echo("✗ Unauthorized. Please login again.", err=True)
    else:
        click.echo(f"✗ Failed to get status: {response.text}", err=True)


@cli.command()
def health():
    """Check system health."""
    response = requests.get(f"{API_BASE_URL}/health")
    
    if response.status_code == 200:
        data = response.json()
        click.echo(f"\nSystem Status: {data['status']}")
        click.echo(f"Version: {data['version']}")
        click.echo("\nComponents:")
        for component, status in data['components'].items():
            icon = "✓" if status in ["healthy", "operational"] else "✗"
            click.echo(f"  {icon} {component}: {status}")
    else:
        click.echo(f"✗ Health check failed: {response.text}", err=True)


if __name__ == '__main__':
    cli()
