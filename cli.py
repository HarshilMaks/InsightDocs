"""Command-line interface for InsightDocs."""
import click
import requests
import json
from pathlib import Path


API_BASE_URL = "http://localhost:8000"


@click.group()
def cli():
    """InsightDocs CLI - Manage documents and queries."""
    pass


@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
def upload(file_path):
    """Upload a document for processing."""
    click.echo(f"Uploading {file_path}...")
    
    with open(file_path, 'rb') as f:
        files = {'file': (Path(file_path).name, f)}
        response = requests.post(f"{API_BASE_URL}/documents/upload", files=files)
    
    if response.status_code == 200:
        data = response.json()
        click.echo(f"✓ Document uploaded successfully!")
        click.echo(f"  Document ID: {data['document_id']}")
        click.echo(f"  Task ID: {data['task_id']}")
    else:
        click.echo(f"✗ Upload failed: {response.text}", err=True)


@cli.command()
@click.argument('query_text')
@click.option('--top-k', default=5, help='Number of results to retrieve')
def query(query_text, top_k):
    """Query documents using natural language."""
    click.echo(f"Processing query: {query_text}")
    
    payload = {
        "query": query_text,
        "top_k": top_k
    }
    response = requests.post(f"{API_BASE_URL}/query/", json=payload)
    
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
            click.echo(f"\n[{i}] (distance: {source['distance']:.4f})")
            click.echo(source['text'][:200] + "..." if len(source['text']) > 200 else source['text'])
    else:
        click.echo(f"✗ Query failed: {response.text}", err=True)


@cli.command()
def list_documents():
    """List all documents."""
    response = requests.get(f"{API_BASE_URL}/documents/")
    
    if response.status_code == 200:
        data = response.json()
        click.echo(f"\nFound {data['total']} document(s):\n")
        for doc in data['documents']:
            click.echo(f"ID: {doc['id']}")
            click.echo(f"  Filename: {doc['filename']}")
            click.echo(f"  Status: {doc['status']}")
            click.echo(f"  Created: {doc['created_at']}")
            click.echo()
    else:
        click.echo(f"✗ Failed to list documents: {response.text}", err=True)


@cli.command()
@click.argument('task_id')
def status(task_id):
    """Check status of a task."""
    response = requests.get(f"{API_BASE_URL}/tasks/{task_id}")
    
    if response.status_code == 200:
        data = response.json()
        click.echo(f"\nTask Status: {data['status']}")
        click.echo(f"Progress: {data['progress']:.1f}%")
        if data.get('error'):
            click.echo(f"Error: {data['error']}")
        if data.get('result'):
            click.echo(f"\nResult:")
            click.echo(json.dumps(data['result'], indent=2))
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
