# RAG QA System Flagship project

A Retrieval-Augmented Generation (RAG) Question-Answering system that leverages AWS services for efficient document retrieval and answer generation.

## Technology Stack

### AWS Services
- **AWS Bedrock Claude 3.5 Sonnet** - For text generation
- **AWS Lambda** - For serverless compute
- **API Gateway** - For REST API endpoints
- **S3** - For storing document indexes

### Core Components
- **FAISS** - For vector similarity search
- **Python 3.12** - Base programming language
- **CloudFormation** - For infrastructure as code

## System Overview

1. **Document Processing**
   - Documents are converted to embeddings
   - FAISS index stores document vectors
   - Index is saved to S3 bucket

2. **Query Processing**
   - User submits question via API
   - System retrieves relevant documents
   - Claude 3 Sonnet generates answers

3. **API Interface**
   - REST API endpoint for queries
   - JSON request/response format
   - CORS-enabled for web access

## Key Features

- Serverless architecture
- Efficient document retrieval
- Context-aware answers
- Easy deployment with CloudFormation
- Scalable and cost-effective




