import os
from dotenv import load_dotenv
import boto3
from langchain_aws import BedrockEmbeddings
from langchain_community.vectorstores import FAISS
import logging
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QASystem:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Initialize Bedrock client
        self.bedrock = boto3.client(
            'bedrock-runtime',
            region_name='us-east-1',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        
        # Initialize Titan embeddings
        self.embeddings = BedrockEmbeddings(
            client=self.bedrock,
            model_id="amazon.titan-embed-text-v1"
        )
        
        # Create a simple test index if none exists
        if not os.path.exists("temp_index"):
            logger.info("Creating new test index...")
            texts = [
                "This is a RAG (Retrieval Augmented Generation) system.",
                "The system uses Amazon Titan embeddings for document search.",
                "Documents are stored in a FAISS vector store for efficient retrieval.",
                "Questions are answered using relevant document context."
            ]
            self.db = FAISS.from_texts(texts, self.embeddings)
            self.db.save_local("temp_index")
            logger.info("✓ Created and saved test index")
        else:
            logger.info("Loading existing index...")
            self.db = FAISS.load_local("temp_index", self.embeddings, allow_dangerous_deserialization=True)
            logger.info("✓ Loaded existing index")
    
    def answer_question(self, question: str, k: int = 2) -> str:
        """Answer a question using RAG"""
        try:
            # Get relevant documents
            docs = self.db.similarity_search(question, k=k)
            
            # Prepare context
            context = "\n\n".join(doc.page_content for doc in docs)
            
            # Generate answer
            prompt = f"""Based on this context:
            ---
            {context}
            ---
            
            Answer this question: {question}
            
            If the context doesn't contain relevant information, say "I don't have enough information to answer that."
            """
            
            import time
            max_retries = 3
            retry_delay = 2
            
            for attempt in range(max_retries):
                try:
                    response = self.bedrock.invoke_model(
                        modelId="anthropic.claude-3-5-sonnet-20240620-v1:0",
                        body=json.dumps({
                            "anthropic_version": "bedrock-2023-05-31",
                            "max_tokens": 500,
                            "messages": [
                                {
                                    "role": "user",
                                    "content": prompt
                                }
                            ]
                        })
                    )
                    break  # Success, exit retry loop
                except Exception as e:
                    if "reached max retries" in str(e) and attempt < max_retries - 1:
                        logger.warning(f"Rate limit hit, retrying in {retry_delay} seconds... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                    else:
                        raise e
            
            response_body = json.loads(response['body'].read())
            answer = response_body['content'][0]['text']
            return answer.strip()
            
        except Exception as e:
            logger.error(f"Error answering question: {str(e)}")
            return f"Error: {str(e)}"

    def search_by_keywords(self, query: str, k: int = 2) -> str:
        """Search using keyword matching instead of semantic search"""
        try:
            # Get all documents from the index using a dummy query
            all_docs = self.db.similarity_search("document", k=100)  # Get many docs
            
            # Filter by keyword matching
            matching_docs = []
            query_lower = query.lower()
            
            for doc in all_docs:
                content_lower = doc.page_content.lower()
                if query_lower in content_lower:
                    matching_docs.append(doc)
            
            if not matching_docs:
                return "I don't have enough information to answer that."
            
            # Use the matching documents
            context = "\n\n".join(doc.page_content for doc in matching_docs[:k])
            
            # Generate answer using the same prompt as before
            prompt = f"""Based on this context:
            ---
            {context}
            ---
            
            Answer this question: {query}
            
            If the context doesn't contain relevant information, say "I don't have enough information to answer that."
            """
            
            # Use your existing Bedrock call
            import time
            max_retries = 3
            retry_delay = 2
            
            for attempt in range(max_retries):
                try:
                    response = self.bedrock.invoke_model(
                        modelId="anthropic.claude-3-5-sonnet-20240620-v1:0",
                        body=json.dumps({
                            "anthropic_version": "bedrock-2023-05-31",
                            "max_tokens": 500,
                            "messages": [
                                {
                                    "role": "user",
                                    "content": prompt
                                }
                            ]
                        })
                    )
                    break
                except Exception as e:
                    if "reached max retries" in str(e) and attempt < max_retries - 1:
                        logger.warning(f"Rate limit hit, retrying in {retry_delay} seconds... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    else:
                        raise e
            
            response_body = json.loads(response['body'].read())
            answer = response_body['content'][0]['text']
            return answer.strip()
            
        except Exception as e:
            logger.error(f"Error in keyword search: {str(e)}")
            return f"Error: {str(e)}"

    def hybrid_search(self, query: str, k: int = 3) -> str:
        """Combines semantic and keyword search for better results"""
        try:
            # Get semantic search results
            semantic_docs = self.db.similarity_search(query, k=k)
            
            # Get keyword search results
            all_docs = self.db.similarity_search("document", k=100)  # Get many docs
            query_lower = query.lower()
            keyword_docs = []
            
            for doc in all_docs:
                content_lower = doc.page_content.lower()
                if query_lower in content_lower:
                    keyword_docs.append(doc)
            
            # Combine and deduplicate results
            combined_docs = []
            seen_content = set()
            
            # Add semantic results first (they're usually more relevant)
            for doc in semantic_docs:
                if doc.page_content not in seen_content:
                    combined_docs.append(doc)
                    seen_content.add(doc.page_content)
            
            # Add keyword results that aren't already included
            for doc in keyword_docs:
                if doc.page_content not in seen_content:
                    combined_docs.append(doc)
                    seen_content.add(doc.page_content)
            
            if not combined_docs:
                return "I don't have enough information to answer that."
            
            # Use the combined documents
            context = "\n\n".join(doc.page_content for doc in combined_docs[:k])
            
            # Generate answer
            prompt = f"""Based on this context:
            ---
            {context}
            ---
            
            Answer this question: {query}
            
            If the context doesn't contain relevant information, say "I don't have enough information to answer that."
            """
            
            # Use your existing Bedrock call with retry logic
            import time
            max_retries = 3
            retry_delay = 2
            
            for attempt in range(max_retries):
                try:
                    response = self.bedrock.invoke_model(
                        modelId="anthropic.claude-3-5-sonnet-20240620-v1:0",
                        body=json.dumps({
                            "anthropic_version": "bedrock-2023-05-31",
                            "max_tokens": 500,
                            "messages": [
                                {
                                    "role": "user",
                                    "content": prompt
                                }
                            ]
                        })
                    )
                    break
                except Exception as e:
                    if "reached max retries" in str(e) and attempt < max_retries - 1:
                        logger.warning(f"Rate limit hit, retrying in {retry_delay} seconds... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    else:
                        raise e
            
            response_body = json.loads(response['body'].read())
            answer = response_body['content'][0]['text']
            return answer.strip()
            
        except Exception as e:
            logger.error(f"Error in hybrid search: {str(e)}")
            return f"Error: {str(e)}"

    def show_available_documents(self, limit: int = 5):
        """Show preview of available documents"""
        if not self.db:
            return "No documents loaded"
            
        try:
            docs = self.db.similarity_search("", k=limit)
            previews = []
            for i, doc in enumerate(docs, 1):
                content = doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
                previews.append(f"\n{i}. Document preview:\n{content}")
            return "\n".join(previews)
        except Exception as e:
            logger.error(f"Error showing documents: {str(e)}")
            return f"Error: {str(e)}"

if __name__ == "__main__":
    # Test the QA system
    print("Initializing QA System...")
    qa = QASystem()
    
    # Show available documents
    print("\nAvailable Documents:")
    print(qa.show_available_documents())
    
    # Test questions
    test_questions = [
        "What is this system?",
        "What kind of embeddings does it use?",
        "How are documents stored?",
        "How does the system answer questions?"
    ]
    
    print("\nQA System Test")
    print("-------------")
    
    for q in test_questions:
        print(f"\nQ: {q}")
        print(f"A: {qa.answer_question(q)}")