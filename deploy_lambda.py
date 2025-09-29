import boto3
import json
import zipfile
import os
import shutil
from botocore.exceptions import ClientError

def create_deployment_package():
    """Create a deployment package for the Lambda function"""
    print("Creating deployment package...")
    
    # Create package directory
    package_dir = "package"
    if os.path.exists(package_dir):
        shutil.rmtree(package_dir)
    os.makedirs(package_dir)
    
    # Copy lambda function
    shutil.copy("lambda_function.py", package_dir)
    
    # Create requirements.txt for Lambda
    requirements = [
        "boto3",
        "botocore"
    ]
    
    with open(os.path.join(package_dir, "requirements.txt"), "w") as f:
        f.write("\n".join(requirements))
    
    # Create zip file
    zip_path = "lambda-deployment.zip"
    if os.path.exists(zip_path):
        os.remove(zip_path)
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(package_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, package_dir)
                zipf.write(file_path, arcname)
    
    print(f"✓ Created deployment package: {zip_path}")
    return zip_path

def deploy_lambda():
    """Deploy the Lambda function using CloudFormation"""
    try:
        print("Deploying Lambda function...")
        
        # Create deployment package
        zip_path = create_deployment_package()
        
        # Upload to S3
        s3_client = boto3.client('s3')
        bucket_name = 'rag-qa-deployment-bucket'  # You can change this
        
        try:
            s3_client.head_bucket(Bucket=bucket_name)
        except ClientError:
            print(f"Creating S3 bucket: {bucket_name}")
            s3_client.create_bucket(Bucket=bucket_name)
        
        # Upload zip file
        s3_key = f"lambda/{zip_path}"
        s3_client.upload_file(zip_path, bucket_name, s3_key)
        print(f"✓ Uploaded to S3: s3://{bucket_name}/{s3_key}")
        
        # Deploy with CloudFormation
        cf_client = boto3.client('cloudformation')
        stack_name = 'rag-qa-stack'
        
        # Read template
        with open('template.yaml', 'r') as f:
            template_body = f.read()
        
        # Update template with actual bucket name
        template_body = template_body.replace('your_bucket_name', bucket_name)
        
        try:
            # Check if stack exists
            cf_client.describe_stacks(StackName=stack_name)
            print("Updating existing stack...")
            response = cf_client.update_stack(
                StackName=stack_name,
                TemplateBody=template_body,
                Capabilities=['CAPABILITY_IAM', 'CAPABILITY_AUTO_EXPAND']
            )
        except ClientError as e:
            if 'does not exist' in str(e):
                print("Creating new stack...")
                response = cf_client.create_stack(
                    StackName=stack_name,
                    TemplateBody=template_body,
                    Capabilities=['CAPABILITY_IAM', 'CAPABILITY_AUTO_EXPAND']
                )
            else:
                raise e
        
        print(f"✓ CloudFormation operation started: {response['StackId']}")
        print("Waiting for deployment to complete...")
        
        # Wait for completion
        waiter = cf_client.get_waiter('stack_create_complete')
        try:
            waiter.wait(StackName=stack_name)
        except:
            # Try update waiter if create failed
            waiter = cf_client.get_waiter('stack_update_complete')
            waiter.wait(StackName=stack_name)
        
        # Get outputs
        response = cf_client.describe_stacks(StackName=stack_name)
        outputs = response['Stacks'][0]['Outputs']
        
        for output in outputs:
            if output['OutputKey'] == 'WebEndpoint':
                api_endpoint = output['OutputValue']
                print(f"\n✅ Deployment successful!")
                print(f"API Endpoint: {api_endpoint}")
                print(f"Test with: curl -X POST {api_endpoint} -H 'Content-Type: application/json' -d '{{\"context\":\"test context\",\"query\":\"test question\"}}'")
                return api_endpoint
        
        print("❌ Deployment completed but no API endpoint found")
        return None
        
    except Exception as e:
        print(f"❌ Deployment failed: {str(e)}")
        return None

if __name__ == "__main__":
    deploy_lambda()
