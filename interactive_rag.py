import os
import time
from advanced_rag import AdvancedRAGSystem

def interactive_rag():
    """Interactive RAG system to avoid rate limiting"""
    
    # Set environment variable
    os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
    
    print("Advanced RAG System - Interactive Mode")
    print("=" * 50)
    print("Type 'quit' to exit")
    print("Type 'help' for examples")
    print()
    
    # Initialize RAG system
    print("Initializing Advanced RAG System...")
    rag = AdvancedRAGSystem()
    print("System ready!\n")
    
    while True:
        try:
            # Get user input
            query = input("Ask a question: ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            
            if query.lower() == 'help':
                print("\nExample queries:")
                print("• What is the use of transformers?")
                print("• How does RAG work?")
                print("• Compare BERT and GPT models")
                print("• Explain the attention mechanism")
                print("• Define machine learning")
                print()
                continue
            
            if not query:
                print("Please enter a question.\n")
                continue
            
            print(f"\nProcessing: {query}")
            print("-" * 50)
            
            # Debug query processing
            debug_info = rag.debug_query_processing(query)
            print(f"Intent: {debug_info['analysis']['intent']}")
            print(f"Entities: {debug_info['analysis']['entities']}")
            print(f"Keywords: {debug_info['analysis']['keywords']}")
            print(f"Search queries: {len(debug_info['search_queries'])}")
            print(f"Confidence: {debug_info['analysis']['confidence']:.2f}")
            
            # Get answer
            print("\nGenerating answer...")
            answer = rag.answer_question(query)
            
            print(f"\nAnswer:")
            print("-" * 30)
            print(answer)
            print("\n" + "="*60 + "\n")
            
            # Add delay to avoid rate limiting
            time.sleep(2)
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {str(e)}")
            print("Please try again.\n")

if __name__ == "__main__":
    interactive_rag()
