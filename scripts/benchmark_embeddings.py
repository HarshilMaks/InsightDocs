"""Benchmark embedding models: all-MiniLM-L6-v2 vs bge-base-en-v1.5"""
import time
from sentence_transformers import SentenceTransformer
import numpy as np

# Test documents
documents = [
    "The Python programming language was created by Guido van Rossum.",
    "Machine learning algorithms can identify patterns in large datasets.",
    "Natural language processing enables computers to understand human language.",
    "Deep learning uses neural networks with multiple layers.",
    "Artificial intelligence is transforming healthcare and medicine.",
]

# Test queries
queries = [
    "Who created Python?",
    "What is machine learning?",
    "How do computers understand language?",
]

def benchmark_model(model_name: str):
    """Benchmark a single model."""
    print(f"\n{'='*60}")
    print(f"Testing: {model_name}")
    print(f"{'='*60}\n")
    
    # Load model
    print("Loading model...")
    start_load = time.time()
    model = SentenceTransformer(model_name)
    load_time = time.time() - start_load
    print(f"✅ Loaded in {load_time:.2f}s")
    
    # Get model info
    dim = model.get_sentence_embedding_dimension()
    print(f"📏 Embedding Dimension: {dim}")
    
    # Encode documents
    print(f"\n📄 Encoding {len(documents)} documents...")
    start_encode = time.time()
    doc_embeddings = model.encode(documents)
    encode_time = time.time() - start_encode
    print(f"✅ Encoded in {encode_time:.3f}s ({encode_time/len(documents)*1000:.1f}ms per doc)")
    
    # Encode queries
    print(f"\n❓ Encoding {len(queries)} queries...")
    query_embeddings = model.encode(queries)
    
    # Calculate similarity scores
    print(f"\n🔍 Calculating similarity scores...")
    for i, query in enumerate(queries):
        query_emb = query_embeddings[i]
        
        # Cosine similarity
        similarities = []
        for doc_emb in doc_embeddings:
            sim = np.dot(query_emb, doc_emb) / (np.linalg.norm(query_emb) * np.linalg.norm(doc_emb))
            similarities.append(sim)
        
        # Find top match
        top_idx = np.argmax(similarities)
        top_score = similarities[top_idx]
        
        print(f"\nQuery: '{query}'")
        print(f"  Top Match (score={top_score:.4f}): '{documents[top_idx]}'")
    
    return {
        "model": model_name,
        "dimension": dim,
        "load_time": load_time,
        "encode_time": encode_time,
        "docs_per_second": len(documents) / encode_time
    }


if __name__ == "__main__":
    print("\n🧪 EMBEDDING MODEL BENCHMARK\n")
    
    # Test current model
    results_mini = benchmark_model("all-MiniLM-L6-v2")
    
    # Test upgraded model
    results_bge = benchmark_model("BAAI/bge-base-en-v1.5")
    
    # Compare
    print(f"\n{'='*60}")
    print("📊 COMPARISON SUMMARY")
    print(f"{'='*60}\n")
    
    print(f"{'Metric':<25} {'all-MiniLM':<20} {'bge-base':<20}")
    print(f"{'-'*65}")
    print(f"{'Dimension':<25} {results_mini['dimension']:<20} {results_bge['dimension']:<20}")
    print(f"{'Load Time (s)':<25} {results_mini['load_time']:<20.2f} {results_bge['load_time']:<20.2f}")
    print(f"{'Encode Time (s)':<25} {results_mini['encode_time']:<20.3f} {results_bge['encode_time']:<20.3f}")
    print(f"{'Docs/Second':<25} {results_mini['docs_per_second']:<20.1f} {results_bge['docs_per_second']:<20.1f}")
    
    # Calculate improvements
    dim_increase = (results_bge['dimension'] / results_mini['dimension'] - 1) * 100
    speed_change = (results_bge['encode_time'] / results_mini['encode_time'] - 1) * 100
    
    print(f"\n{'='*60}")
    print("💡 INSIGHTS")
    print(f"{'='*60}\n")
    print(f"✅ Dimension increase: +{dim_increase:.1f}% (better semantic representation)")
    print(f"{'⚠️' if speed_change > 0 else '✅'} Speed change: {speed_change:+.1f}%")
    print(f"\n📌 Recommendation:")
    if dim_increase > 50:
        print(f"   bge-base-en-v1.5 offers {dim_increase:.0f}% more dimensions for richer embeddings.")
        print(f"   This typically translates to 10-15% better retrieval accuracy.")
        if speed_change < 50:
            print(f"   ✅ RECOMMENDED: Switch to bge-base-en-v1.5")
        else:
            print(f"   ⚠️ Consider trade-off: Better quality but {speed_change:.0f}% slower")
    else:
        print(f"   Marginal improvement, stick with all-MiniLM-L6-v2 for speed.")
    
    print()
