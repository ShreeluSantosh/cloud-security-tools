"""
S3 Tools: A collection of tools for managing and securing Amazon S3 buckets.

Classes:
- S3Basics: Base class for S3 tools, providing common functionality for credential management 
    and logging.
    Methods: 
    - _setup_logging: Set up logging for the S3 tools.
    - _fetch_credentials: Fetch AWS credentials from a configuration file or environment variables.
    - setup: Set up logging for the S3 tools and create an S3 client using the fetched credentials.

- S3PublicBuckets: Class to check if S3 buckets are publicly accessible.
    Methods:
    - check_s3_bucket_public_access: Check if S3 buckets are publicly accessible.
"""

import json
import logging
import os
import boto3
from botocore.exceptions import ClientError

class S3Basics:
    """Base class for S3 tools, providing common functionality for credential management and logging."""

    def __init__(self):
        """Initialize the S3Basics class."""
        self.aws_access_key_id = None
        self.aws_secret_access_key = None
        self.s3_client = None
        self.logger = None
    
    def _setup_logging(self, name='', level=logging.INFO, format_string=None):
        """
        Set up logging for the S3 tools.

        Args:
            name (str): Log name (default: '')
            level (int): Logging level, e.g. logging.INFO (default: logging.INFO)
            format_string (str): Log message format (default: "%(asctime)s %(name)s [%(levelname)s] %(message)s")
        """
        logging.basicConfig(level=level)
        self.logger = logging.getLogger(name)
        if format_string:
            formatter = logging.Formatter(format_string)
            self.logger.handlers[0].setFormatter(formatter)

    def _fetch_credentials(self):
        """
        Fetch AWS credentials from a configuration file or environment variables.
        """
        # read credentials from a config file (e.g., s3-config.json)
        try:
            # first check if the s3-config.json file exists and contains the necessary credentials
            self.logger.info("Attempting to fetch AWS credentials from environment variables.")
            if not os.path.exists('s3-config.json'):
                self.aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
                self.aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
                if not self.aws_access_key_id or not self.aws_secret_access_key:
                    self.logger.error("AWS credentials not found in environment variables.")

            self.logger.info("Attempting to fetch AWS credentials from configuration file.")
            with open('s3-config.json', 'r') as f:
                config = json.load(f)
                self.aws_access_key_id = config.get('aws_access_key_id')
                self.aws_secret_access_key = config.get('aws_secret_access_key')
                if not self.aws_access_key_id or not self.aws_secret_access_key:
                    self.logger.error("AWS credentials not found in configuration file.")
        except FileNotFoundError:
            self.logger.error("Configuration file not found. Please provide AWS credentials.")

    def setup(self):
        """
        Set up logging for the S3 tools and create an S3 client using the fetched credentials.
        """
        self._setup_logging(
            "s3-tools", 
            logging.INFO, 
            "%(asctime)s %(name)s [%(levelname)s] %(message)s"
            )
        try:
            self._fetch_credentials()
            self.s3_client = boto3.client(
                's3', 
                aws_access_key_id=self.aws_access_key_id, 
                aws_secret_access_key=self.aws_secret_access_key
                )
        except Exception as e:
            self.logger.error("Error setting up S3 client: {%s}", e)
        

class S3PublicBuckets(S3Basics):
    """Class to check if S3 buckets are publicly accessible."""

    def __init__(self):
        """Initialize the S3PublicBuckets class."""
        super().__init__()


    def check_s3_bucket_public_access(self, bucket_names_list):
        """
        Check if S3 buckets are publicly accessible.
        
        Args:
            bucket_names_list (list): List of S3 bucket names to check
        
        Returns:
            Dictionary with bucket names and their public access status
        """
        self._fetch_credentials()
        if not self.aws_access_key_id or not self.aws_secret_access_key:
            self.logger.error("Failed to fetch AWS credentials.")
            return {}
        
        results = {}

        for bucket_name in bucket_names_list:
            self.logger.info("Checking public access for bucket: {%s}", bucket_name)
            try:
                public_access_block = self.s3_client.get_public_access_block(
                    Bucket=bucket_name
                )

                config = public_access_block['PublicAccessBlockConfiguration']
                is_public = not (
                    config['BlockPublicAcls'] and
                    config['BlockPublicPolicy'] and
                    config['IgnorePublicAcls'] and
                    config['RestrictPublicBuckets']
                )

                results[bucket_name] = {
                    'is_public': is_public,
                    'status': 'FLAGGED' if is_public else 'SAFE'
                }

            except ClientError as e:
                self.logger.error("Error occurred while checking bucket {%s}: {%s}", bucket_name, e)
                results[bucket_name] = {
                    'is_public': None,
                    'status': f'ERROR: {e.response["Error"]["Code"]}'
                }

        return results
    
