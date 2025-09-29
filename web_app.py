import http.server
import socketserver
import webbrowser
import json
import boto3
import requests
import logging
from urllib.parse import parse_qs, urlparse

# Set up logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_api_endpoint():
    cf_client = boto3.client('cloudformation')
    try:
        response = cf_client.describe_stacks(StackName='rag-qa-stack')
        outputs = response['Stacks'][0]['Outputs']
        for output in outputs:
            if output['OutputKey'] == 'WebEndpoint':
                return output['OutputValue']
    except Exception as e:
        logger.error(f"Error getting endpoint: {str(e)}")
    return None

def get_s3_bucket():
    cf_client = boto3.client('cloudformation')
    try:
        response = cf_client.describe_stacks(StackName='rag-qa-stack')
        outputs = response['Stacks'][0]['Outputs']
        for output in outputs:
            if output['OutputKey'] == 'S3BucketName':
                return output['OutputValue']
    except Exception as e:
        logger.error(f"Error getting S3 bucket: {str(e)}")
    return None

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Q&A System</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            max-width: 1200px;
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
        input { 
            width: 100%; 
            margin: 10px 0; 
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 16px;
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
        #answer { 
            margin-top: 20px; 
            padding: 15px; 
            background: #f8f9fa; 
            border-radius: 4px;
            border-left: 4px solid #2196F3;
            white-space: pre-wrap;
            max-height: none;
            overflow-y: visible;
        }
        .loading { 
            display: none;
            color: #666;
            margin-top: 20px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Q&A System</h1>
        
        <div>
            <input type="text" id="question" placeholder="Ask your question..." autofocus>
        </div>
        
        <div style="margin: 15px 0;">
            <label style="margin-right: 20px;">
                <input type="radio" name="searchType" value="hybrid" checked> Hybrid Search (Recommended)
            </label>
            <label style="margin-right: 20px;">
                <input type="radio" name="searchType" value="semantic"> Semantic Search
            </label>
            <label>
                <input type="radio" name="searchType" value="keyword"> Keyword Search
            </label>
        </div>
        
        <button id="askButton">Ask Question</button>
        
        <div id="loading" class="loading">Getting answer...</div>
        <div id="answer"></div>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const askButton = document.getElementById('askButton');
            const questionInput = document.getElementById('question');
            const answerDiv = document.getElementById('answer');
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
                    answerDiv.innerHTML = '';
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
                        answerDiv.innerHTML = data.answer.replace(/\\n/g, '<br>');
                        answerDiv.innerHTML += `<br><br><small>Search type: ${data.search_type}</small>`;
                    } else {
                        answerDiv.innerHTML = `Error: ${data.error || 'Could not get an answer. Please try again.'}`;
                    }
                } catch (error) {
                    console.error('Error:', error);
                    answerDiv.innerHTML = `Error: ${error.message}`;
                } finally {
                    loadingDiv.style.display = 'none';
                    askButton.disabled = false;
                }
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
    def __init__(self, *args, **kwargs):
        # Cache the document content
        self._document_content = None
        super().__init__(*args, **kwargs)

    def get_document_content(self):
        """Get processed document content from S3 with caching"""
        if self._document_content is None:
            try:
                s3_client = boto3.client('s3')
                bucket_name = get_s3_bucket()
                
                response = s3_client.list_objects_v2(
                    Bucket=bucket_name,
                    Prefix='documents/text/'
                )
                
                all_content = []
                for obj in response.get('Contents', []):
                    content = s3_client.get_object(
                        Bucket=bucket_name,
                        Key=obj['Key']
                    )['Body'].read().decode('utf-8')
                    all_content.append(content)
                
                self._document_content = "\n\n".join(all_content)
            except Exception as e:
                logger.error(f"Error getting document content: {str(e)}")
                return ""
        
        return self._document_content

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
                # Import and use the local QA system
                from qa_system import QASystem
                import os
                os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
                
                qa_system = QASystem()
                
                # Get search type and query
                search_type = request_data.get('search_type', 'hybrid')  # Default to hybrid
                query = request_data['query']
                
                if search_type == 'semantic':
                    answer = qa_system.answer_question(query)
                elif search_type == 'keyword':
                    answer = qa_system.search_by_keywords(query)
                elif search_type == 'hybrid':
                    answer = qa_system.hybrid_search(query)
                else:
                    answer = qa_system.hybrid_search(query)  # Default to hybrid
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'answer': answer,
                    'search_type': search_type
                }).encode())
                
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
        print(f"Server running at http://localhost:{port}")
        webbrowser.open(f"http://localhost:{port}")
        httpd.serve_forever()

if __name__ == "__main__":
    run_server()
    run_server()