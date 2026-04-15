import json
import socket
import time
import os


def lambda_handler(event, context):
    print("=== Lambda Diagnostic Test ===")

    # Test 1: Basic environment
    print(f"AWS_REGION: {os.environ.get('AWS_REGION', 'Not set')}")
    print(f"AWS_DEFAULT_REGION: {os.environ.get('AWS_DEFAULT_REGION', 'Not set')}")

    # Test 2: DNS Resolution
    try:
        print("Testing DNS resolution...")
        s3_ip = socket.gethostbyname('s3.ap-southeast-1.amazonaws.com')
        print(f"s3.ap-southeast-1.amazonaws.com resolves to: {s3_ip}")

        sts_ip = socket.gethostbyname('sts.ap-southeast-1.amazonaws.com')
        print(f"sts.ap-southeast-1.amazonaws.com resolves to: {sts_ip}")
    except Exception as e:
        print(f"DNS resolution failed: {e}")
        return {"statusCode": 500, "body": f"DNS failed: {e}"}

    # Test 3: Network connectivity
    try:
        print("Testing network connectivity...")
        import urllib3
        http = urllib3.PoolManager()

        # Test external connectivity
        resp = http.request('GET', 'https://httpbin.org/ip', timeout=10)
        print(f"External IP test: {resp.status}")

        # Test AWS connectivity
        resp = http.request('GET', 'https://s3.ap-southeast-1.amazonaws.com', timeout=10)
        print(f"S3 endpoint test: {resp.status}")

    except Exception as e:
        print(f"Network connectivity failed: {e}")
        return {"statusCode": 500, "body": f"Network failed: {e}"}

    # Test 4: boto3 import
    try:
        print("Testing boto3 import...")
        import boto3
        print("boto3 imported successfully")

        # Test STS first (simpler than S3)
        print("Creating STS client...")
        sts = boto3.client('sts', region_name='ap-southeast-1')
        print("STS client created successfully")

        print("Getting caller identity...")
        identity = sts.get_caller_identity()
        print(f"Caller identity: {identity.get('Account', 'Unknown')}")

    except Exception as e:
        print(f"boto3 test failed: {e}")
        return {"statusCode": 500, "body": f"boto3 failed: {e}"}

    # Test 5: S3 client
    try:
        print("Creating S3 client...")
        s3 = boto3.client('s3', region_name='ap-southeast-1')
        print("S3 client created successfully!")

        return {"statusCode": 200, "body": "All tests passed!"}

    except Exception as e:
        print(f"S3 client creation failed: {e}")
        return {"statusCode": 500, "body": f"S3 client failed: {e}"}
