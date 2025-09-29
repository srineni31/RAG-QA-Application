import re
import json
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import boto3
import os
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QueryIntent(Enum):
    """Query intent classification"""
    FACTUAL = "factual"  # What is X? Who is Y?
    COMPARATIVE = "comparative"  # Compare X and Y
    PROCEDURAL = "procedural"  # How to do X?
    ANALYTICAL = "analytical"  # Why does X happen?
    DEFINITIONAL = "definitional"  # Define X
    TEMPORAL = "temporal"  # When did X happen?
    CAUSAL = "causal"  # What causes X?
    UNKNOWN = "unknown"

@dataclass
class QueryAnalysis:
    """Structured analysis of a query"""
    original_query: str
    intent: QueryIntent
    entities: List[str]
    keywords: List[str]
    expanded_terms: List[str]
    reformulated_queries: List[str]
    confidence: float

class QueryProcessor:
    """Advanced query processing with expansion, reformulation, and intent understanding"""
    
    def __init__(self):
        load_dotenv()
        
        # Initialize Bedrock client for LLM-based processing
        self.bedrock = boto3.client(
            'bedrock-runtime',
            region_name='us-east-1',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        
        # Intent patterns
        self.intent_patterns = {
            QueryIntent.FACTUAL: [
                r'what is', r'what are', r'who is', r'who are', 
                r'which is', r'which are', r'where is', r'where are'
            ],
            QueryIntent.COMPARATIVE: [
                r'compare', r'difference', r'versus', r'vs', 
                r'better than', r'worse than', r'advantage', r'disadvantage'
            ],
            QueryIntent.PROCEDURAL: [
                r'how to', r'how do', r'how can', r'how does',
                r'steps to', r'process of', r'method to'
            ],
            QueryIntent.ANALYTICAL: [
                r'why', r'explain', r'analyze', r'reason for',
                r'cause of', r'purpose of'
            ],
            QueryIntent.DEFINITIONAL: [
                r'define', r'definition', r'meaning of', r'what does.*mean'
            ],
            QueryIntent.TEMPORAL: [
                r'when', r'time', r'date', r'history', r'timeline'
            ],
            QueryIntent.CAUSAL: [
                r'causes', r'results in', r'leads to', r'because of'
            ]
        }
        
        # Common synonyms and related terms
        self.synonym_dict = {
            'transformer': ['transformer model', 'attention mechanism', 'self-attention', 'BERT', 'GPT'],
            'RAG': ['retrieval augmented generation', 'retrieval generation', 'document retrieval'],
            'machine learning': ['ML', 'artificial intelligence', 'AI', 'deep learning'],
            'neural network': ['neural net', 'deep learning model', 'AI model'],
            'algorithm': ['method', 'technique', 'approach', 'procedure'],
            'data': ['information', 'dataset', 'records', 'facts'],
            'model': ['system', 'framework', 'architecture', 'approach'],
            'training': ['learning', 'optimization', 'fitting', 'education'],
            'performance': ['accuracy', 'efficiency', 'effectiveness', 'quality'],
            'optimization': ['improvement', 'enhancement', 'tuning', 'refinement']
        }
    
    def analyze_query(self, query: str) -> QueryAnalysis:
        """Comprehensive query analysis"""
        logger.info(f"Analyzing query: {query}")
        
        # Clean and preprocess query
        cleaned_query = self._clean_query(query)
        
        # Extract entities and keywords
        entities = self._extract_entities(cleaned_query)
        keywords = self._extract_keywords(cleaned_query)
        
        # Classify intent
        intent = self._classify_intent(cleaned_query)
        
        # Expand query with synonyms
        expanded_terms = self._expand_query(cleaned_query)
        
        # Reformulate queries
        reformulated_queries = self._reformulate_query(cleaned_query, intent)
        
        # Calculate confidence
        confidence = self._calculate_confidence(cleaned_query, intent, entities)
        
        return QueryAnalysis(
            original_query=query,
            intent=intent,
            entities=entities,
            keywords=keywords,
            expanded_terms=expanded_terms,
            reformulated_queries=reformulated_queries,
            confidence=confidence
        )
    
    def _clean_query(self, query: str) -> str:
        """Clean and normalize query"""
        # Remove extra whitespace
        query = re.sub(r'\s+', ' ', query.strip())
        
        # Remove special characters but keep important ones
        query = re.sub(r'[^\w\s\?\!\.]', ' ', query)
        
        # Convert to lowercase for processing
        return query.lower()
    
    def _extract_entities(self, query: str) -> List[str]:
        """Extract named entities from query"""
        entities = []
        
        # Simple entity extraction (can be enhanced with NER models)
        # Look for capitalized words and technical terms
        words = query.split()
        for word in words:
            if word.isupper() or word.istitle():
                entities.append(word)
        
        # Add technical terms
        tech_terms = ['transformer', 'RAG', 'BERT', 'GPT', 'LLM', 'NLP', 'ML', 'AI']
        for term in tech_terms:
            if term in query:
                entities.append(term)
        
        return list(set(entities))
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract important keywords from query"""
        # Remove stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those'}
        
        words = query.split()
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        
        return keywords
    
    def _classify_intent(self, query: str) -> QueryIntent:
        """Classify query intent using pattern matching"""
        query_lower = query.lower()
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    return intent
        
        return QueryIntent.UNKNOWN
    
    def _expand_query(self, query: str) -> List[str]:
        """Expand query with synonyms and related terms"""
        expanded_terms = []
        words = query.split()
        
        for word in words:
            if word in self.synonym_dict:
                expanded_terms.extend(self.synonym_dict[word])
        
        return list(set(expanded_terms))
    
    def _reformulate_query(self, query: str, intent: QueryIntent) -> List[str]:
        """Generate alternative query formulations"""
        reformulations = []
        
        if intent == QueryIntent.FACTUAL:
            # Add "explain" and "describe" variations
            if not query.startswith('explain'):
                reformulations.append(f"explain {query}")
            if not query.startswith('describe'):
                reformulations.append(f"describe {query}")
        
        elif intent == QueryIntent.PROCEDURAL:
            # Add step-by-step variations
            reformulations.append(f"step by step {query}")
            reformulations.append(f"process of {query}")
        
        elif intent == QueryIntent.COMPARATIVE:
            # Add analysis variations
            reformulations.append(f"analysis of {query}")
            reformulations.append(f"pros and cons of {query}")
        
        # Add general reformulations
        reformulations.append(f"information about {query}")
        reformulations.append(f"details on {query}")
        
        return reformulations
    
    def _calculate_confidence(self, query: str, intent: QueryIntent, entities: List[str]) -> float:
        """Calculate confidence score for query analysis"""
        confidence = 0.5  # Base confidence
        
        # Boost confidence for clear intent
        if intent != QueryIntent.UNKNOWN:
            confidence += 0.2
        
        # Boost confidence for entities
        if entities:
            confidence += min(0.2, len(entities) * 0.1)
        
        # Boost confidence for longer queries
        if len(query.split()) > 3:
            confidence += 0.1
        
        return min(1.0, confidence)
    
    def generate_search_queries(self, analysis: QueryAnalysis) -> List[str]:
        """Generate multiple search queries for retrieval"""
        search_queries = [analysis.original_query]
        
        # Add reformulated queries
        search_queries.extend(analysis.reformulated_queries)
        
        # Add expanded term queries
        for term in analysis.expanded_terms:
            search_queries.append(f"{analysis.original_query} {term}")
        
        # Add entity-based queries
        for entity in analysis.entities:
            search_queries.append(f"{entity} {analysis.original_query}")
        
        return list(set(search_queries))  # Remove duplicates
    
    def process_with_llm(self, query: str) -> Dict:
        """Use LLM for advanced query processing"""
        try:
            prompt = f"""Analyze this query and provide structured information:

Query: "{query}"

Please provide:
1. Intent classification (factual, procedural, comparative, analytical, definitional, temporal, causal)
2. Key entities mentioned
3. Important keywords
4. 3 alternative query formulations
5. Related concepts or synonyms

Format as JSON:
{{
    "intent": "intent_type",
    "entities": ["entity1", "entity2"],
    "keywords": ["keyword1", "keyword2"],
    "alternative_queries": ["alt1", "alt2", "alt3"],
    "related_concepts": ["concept1", "concept2"]
}}"""

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
            
            response_body = json.loads(response['body'].read())
            llm_response = response_body['content'][0]['text']
            
            # Try to parse JSON from LLM response
            try:
                # Extract JSON from response
                json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            except json.JSONDecodeError:
                logger.warning("Failed to parse LLM JSON response")
            
            return {"error": "Failed to parse LLM response"}
            
        except Exception as e:
            logger.error(f"Error in LLM processing: {str(e)}")
            return {"error": str(e)}

def main():
    """Test the query processor"""
    processor = QueryProcessor()
    
    test_queries = [
        "What is the use of transformers?",
        "How does RAG work?",
        "Compare BERT and GPT models",
        "Explain the attention mechanism",
        "What causes overfitting in neural networks?"
    ]
    
    print("=== Query Processing Test ===\n")
    
    for query in test_queries:
        print(f"Query: {query}")
        print("-" * 50)
        
        # Basic analysis
        analysis = processor.analyze_query(query)
        print(f"Intent: {analysis.intent.value}")
        print(f"Entities: {analysis.entities}")
        print(f"Keywords: {analysis.keywords}")
        print(f"Expanded terms: {analysis.expanded_terms}")
        print(f"Reformulated queries: {analysis.reformulated_queries}")
        print(f"Confidence: {analysis.confidence:.2f}")
        
        # Generate search queries
        search_queries = processor.generate_search_queries(analysis)
        print(f"Search queries: {search_queries}")
        
        print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    main()
