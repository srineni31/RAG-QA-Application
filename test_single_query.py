import os
import time
from advanced_rag import AdvancedRAGSystem

def test_single_query():
    """Test a single query to avoid rate limiting"""
    
    # Set environment variable
    os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
    
    print("Initializing Advanced RAG System...")
    rag = AdvancedRAGSystem()
    
    # Test with a single query
    query = "What is the use of transformers?"
    
    print(f"\nTesting query: {query}")
    print("-" * 60)
    
    # Debug query processing
    debug_info = rag.debug_query_processing(query)
    print(f"Intent: {debug_info['analysis']['intent']}")
    print(f"Entities: {debug_info['analysis']['entities']}")
    print(f"Keywords: {debug_info['analysis']['keywords']}")
    print(f"Search queries: {debug_info['search_queries']}")
    print(f"Total queries: {debug_info['total_queries']}")
    
    # Get answer
    print("\nGenerating answer...")
    answer = rag.answer_question(query)
    print(f"\nAnswer: {answer}")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    test_single_query()
