import json
import boto3
import os
import logging
from botocore.exceptions import ClientError
from datetime import datetime

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def invoke_bedrock(prompt, model_id="anthropic.claude-v2"):
    """Invoke Bedrock model with the given prompt"""
    bedrock = boto3.client('bedrock-runtime')
    
    try:
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "temperature": 0.1,
            "messages": [
                {
                    "role": "user",
                    "content": f"""Given the following context, please answer the question. Keep your response concise and relevant.

Context: {prompt['context']}

Question: {prompt['query']}

Answer the question based only on the provided context. If the context doesn't contain enough information to answer the question, say so."""
                }
            ]
        })
        
        response = bedrock.invoke_model(
            modelId=model_id,
            body=body
        )
        
        response_body = json.loads(response['body'].read())
        return response_body['content'][0]['text']
        
    except Exception as e:
        print(f"Error invoking Bedrock: {str(e)}")
        raise

def store_qa_history(query, context, answer, bucket_name):
    """Store QA interaction history in S3"""
    try:
        s3 = boto3.client('s3')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        qa_record = {
            'timestamp': timestamp,
            'query': query,
            'context': context,
            'answer': answer
        }
        
        key = f'qa_history/{timestamp}.json'
        s3.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=json.dumps(qa_record, indent=2)
        )
        return key
    except Exception as e:
        print(f"Error storing QA history: {str(e)}")
        # Continue execution even if history storage fails
        return None

def lambda_handler(event, context):
    try:
        # Log the incoming event
        logger.info("Starting Lambda execution")
        logger.info(f"Event: {json.dumps(event)}")
        
        # Parse input
        logger.info("Parsing input body")
        body = json.loads(event['body'])
        context_text = body.get('context', '')
        query = body.get('query', '')
        
        if not context_text or not query:
            logger.warning("Missing required parameters")
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Both context and query are required'
                })
            }
        
        # Initialize Bedrock client
        logger.info("Initializing Bedrock client")
        bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
        
        # Get IAM identity for debugging
        try:
            sts = boto3.client('sts')
            identity = sts.get_caller_identity()
            logger.info("Current IAM Identity:")
            logger.info(json.dumps(identity, indent=2))
        except Exception as e:
            logger.error(f"Error getting identity: {str(e)}")
        
        # Prepare the request payload
        model_id = 'anthropic.claude-3-sonnet-20240229-v1:0'
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "messages": [
                {
                    "role": "user",
                    "content": f"""You are a helpful assistant that answers questions based on the provided documents.
                    
                    Here are your instructions:
                    1. Read the provided document content carefully
                    2. Answer the question using ONLY information found in the documents
                    3. If you can't find a specific answer in the documents, say "I cannot find an answer to this question in the provided documents"
                    4. When you find relevant information, quote it directly using "quotes"
                    5. Be specific and precise in your answers
                    6. Do not truncate or summarize the answer - provide complete information
                    
                    Document content:
                    {context_text}
                    
                    Question: {query}
                    
                    Answer:"""
                }
            ]
        }
        
        logger.info(f"Invoking model: {model_id}")
        logger.info(f"Request body: {json.dumps(request_body)}")
        
        # Invoke model
        try:
            response = bedrock.invoke_model(
                modelId=model_id,
                body=json.dumps(request_body)
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            logger.info(f"Bedrock response: {json.dumps(response_body)}")
            
            answer = response_body['content'][0]['text']
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'answer': answer
                })
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            request_id = e.response['ResponseMetadata'].get('RequestId', 'N/A')
            
            logger.error("Bedrock ClientError Details:")
            logger.error(f"Error Code: {error_code}")
            logger.error(f"Error Message: {error_message}")
            logger.error(f"Request ID: {request_id}")
            logger.error(f"Full error response: {json.dumps(e.response)}")
            
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Bedrock access error',
                    'details': {
                        'code': error_code,
                        'message': error_message,
                        'requestId': request_id,
                        'modelId': model_id
                    }
                })
            }
            
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Internal server error',
                'details': str(e)
            })
        } 