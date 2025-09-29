import http.server
import socketserver
import webbrowser
import json
import logging
from urllib.parse import parse_qs, urlparse

# Set up logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Advanced RAG System</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            max-width: 1400px;
            margin: 0 auto; 
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
            color: #333;
        }
        .search-section {
            margin-bottom: 20px;
        }
        input[type="text"] { 
            width: 100%; 
            margin: 10px 0; 
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 16px;
        }
        .search-options {
            display: flex;
            gap: 20px;
            margin: 15px 0;
            flex-wrap: wrap;
        }
        .search-option {
            display: flex;
            align-items: center;
            gap: 5px;
        }
        button { 
            background: #2196F3; 
            color: white; 
            padding: 12px 24px; 
            border: none; 
            border-radius: 4px;
            cursor: pointer; 
            font-size: 16px;
            margin-top: 10px;
        }
        button:hover { 
            background: #1976D2; 
        }
        button:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .results {
            margin-top: 20px;
        }
        .answer-section {
            margin-bottom: 20px;
            padding: 15px; 
            background: #f8f9fa; 
            border-radius: 4px;
            border-left: 4px solid #2196F3;
            white-space: pre-wrap;
        }
        .debug-section {
            margin-top: 20px;
            padding: 15px;
            background: #f0f0f0;
            border-radius: 4px;
            border-left: 4px solid #4CAF50;
        }
        .debug-title {
            font-weight: bold;
            margin-bottom: 10px;
            color: #2E7D32;
        }
        .debug-item {
            margin: 5px 0;
            padding: 5px;
            background: white;
            border-radius: 3px;
        }
        .loading { 
            display: none;
            color: #666;
            margin-top: 20px;
            text-align: center;
        }
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #2196F3;
            border-radius: 50%;
            width: 20px;
            height: 20px;
            animation: spin 1s linear infinite;
            display: inline-block;
            margin-right: 10px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .metadata {
            font-size: 12px;
            color: #666;
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px solid #ddd;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Advanced RAG System</h1>
            <p>Query Processing with Expansion, Reformulation & Intent Understanding</p>
        </div>
        
        <div class="search-section">
            <input type="text" id="question" placeholder="Ask your question..." autofocus>
            
            <div class="search-options">
                <div class="search-option">
                    <input type="radio" name="searchType" value="advanced" checked>
                    <label>Advanced RAG (Recommended)</label>
                </div>
                <div class="search-option">
                    <input type="radio" name="searchType" value="hybrid">
                    <label>Hybrid Search</label>
                </div>
                <div class="search-option">
                    <input type="radio" name="searchType" value="semantic">
                    <label>Semantic Search</label>
                </div>
                <div class="search-option">
                    <input type="radio" name="searchType" value="keyword">
                    <label>Keyword Search</label>
                </div>
            </div>
            
            <button id="askButton">Ask Question</button>
        </div>
        
        <div id="loading" class="loading">
            <div class="spinner"></div>
            Processing your question...
        </div>
        
        <div id="results" class="results"></div>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const askButton = document.getElementById('askButton');
            const questionInput = document.getElementById('question');
            const resultsDiv = document.getElementById('results');
            const loadingDiv = document.getElementById('loading');

            async function askQuestion() {
                const question = questionInput.value;
                const searchType = document.querySelector('input[name="searchType"]:checked').value;
                
                if (!question) {
                    alert('Please enter a question');
                    return;
                }
                
                try {
                    console.log('Sending question:', question, 'Search type:', searchType);
                    loadingDiv.style.display = 'block';
                    resultsDiv.innerHTML = '';
                    askButton.disabled = true;
                    
                    const response = await fetch('/ask', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            query: question,
                            search_type: searchType
                        })
                    });
                    
                    console.log('Response status:', response.status);
                    
                    const data = await response.json();
                    console.log('Response data:', data);
                    
                    if (response.ok && data.answer) {
                        displayResults(data);
                    } else {
                        resultsDiv.innerHTML = `<div class="answer-section">Error: ${data.error || 'Could not get an answer. Please try again.'}</div>`;
                    }
                } catch (error) {
                    console.error('Error:', error);
                    resultsDiv.innerHTML = `<div class="answer-section">Error: ${error.message}</div>`;
                } finally {
                    loadingDiv.style.display = 'none';
                    askButton.disabled = false;
                }
            }

            function displayResults(data) {
                let html = '';
                
                // Main answer
                html += `<div class="answer-section">${data.answer.replace(/\\n/g, '<br>')}</div>`;
                
                // Debug information for advanced RAG
                if (data.search_type === 'advanced' && data.debug_info) {
                    html += `<div class="debug-section">`;
                    html += `<div class="debug-title">Query Processing Debug Info</div>`;
                    
                    const debug = data.debug_info;
                    html += `<div class="debug-item"><strong>Intent:</strong> ${debug.analysis.intent}</div>`;
                    html += `<div class="debug-item"><strong>Entities:</strong> ${debug.analysis.entities.join(', ')}</div>`;
                    html += `<div class="debug-item"><strong>Keywords:</strong> ${debug.analysis.keywords.join(', ')}</div>`;
                    html += `<div class="debug-item"><strong>Expanded Terms:</strong> ${debug.analysis.expanded_terms.join(', ')}</div>`;
                    html += `<div class="debug-item"><strong>Confidence:</strong> ${debug.analysis.confidence.toFixed(2)}</div>`;
                    html += `<div class="debug-item"><strong>Total Search Queries:</strong> ${debug.total_queries}</div>`;
                    
                    if (debug.search_queries && debug.search_queries.length > 0) {
                        html += `<div class="debug-item"><strong>Search Queries Used:</strong></div>`;
                        html += `<ul>`;
                        debug.search_queries.forEach(query => {
                            html += `<li>${query}</li>`;
                        });
                        html += `</ul>`;
                    }
                    
                    html += `</div>`;
                }
                
                // Metadata
                html += `<div class="metadata">`;
                html += `Search type: ${data.search_type}`;
                if (data.retrieval_method) {
                    html += ` | Retrieval method: ${data.retrieval_method}`;
                }
                if (data.documents_used) {
                    html += ` | Documents used: ${data.documents_used}`;
                }
                html += `</div>`;
                
                resultsDiv.innerHTML = html;
            }

            // Add click handler
            askButton.addEventListener('click', askQuestion);

            // Add Enter key support
            questionInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    askQuestion();
                }
            });
        });
    </script>
</body>
</html>
"""

class RequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(HTML.encode())

    def do_POST(self):
        if self.path == '/ask':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode('utf-8'))

            try:
                # Import and use the advanced RAG system
                from advanced_rag import AdvancedRAGSystem
                from qa_system import QASystem
                import os
                os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
                
                # Get search type and query
                search_type = request_data.get('search_type', 'advanced')
                query = request_data['query']
                
                response_data = {
                    'answer': '',
                    'search_type': search_type,
                    'debug_info': None
                }
                
                if search_type == 'advanced':
                    # Use advanced RAG system
                    advanced_rag = AdvancedRAGSystem()
                    answer = advanced_rag.answer_question(query)
                    debug_info = advanced_rag.debug_query_processing(query)
                    
                    response_data['answer'] = answer
                    response_data['debug_info'] = debug_info
                    response_data['retrieval_method'] = 'multi_stage'
                    response_data['documents_used'] = len(debug_info.get('search_queries', []))
                
                else:
                    # Use basic RAG system
                    qa_system = QASystem()
                    
                    if search_type == 'semantic':
                        answer = qa_system.answer_question(query)
                    elif search_type == 'keyword':
                        answer = qa_system.search_by_keywords(query)
                    elif search_type == 'hybrid':
                        answer = qa_system.hybrid_search(query)
                    else:
                        answer = qa_system.answer_question(query)
                    
                    response_data['answer'] = answer
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response_data).encode())
                
            except Exception as e:
                logger.error(f"Error processing question: {str(e)}")
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'error': f'Error processing question: {str(e)}'
                }).encode())

def run_server(port=8000):
    with socketserver.TCPServer(("", port), RequestHandler) as httpd:
        print(f"Advanced RAG Server running at http://localhost:{port}")
        webbrowser.open(f"http://localhost:{port}")
        httpd.serve_forever()

if __name__ == "__main__":
    run_server()
