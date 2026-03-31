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
    """Base class for S3 tools, providing common functionality for credential 
    management and logging."""

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
        self.logger = logging.getLogger(name or __name__)
        self.logger.setLevel(level)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            self.logger.addHandler(handler)

        if format_string:
            formatter = logging.Formatter(format_string)
            for handler in self.logger.handlers:
                handler.setFormatter(formatter)

        self.logger.propagate = False

    def _fetch_credentials(self):
        """
        Fetch AWS credentials from a configuration file or environment variables.
        """
        if self.logger is None:
            self._setup_logging("s3-tools")

        self.logger.info("Attempting to fetch AWS credentials.")

        config_path = 's3-config.json'
        config = {}

        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError) as exc:
                self.logger.error("Unable to read configuration file: %s", exc)

        self.aws_access_key_id = config.get('aws_access_key_id') or os.getenv('AWS_ACCESS_KEY_ID')
        self.aws_secret_access_key = config.get('aws_secret_access_key') or os.getenv('AWS_SECRET_ACCESS_KEY')

        if not self.aws_access_key_id or not self.aws_secret_access_key:
            self.logger.warning(
                "AWS credentials were not found in s3-config.json or environment variables; "
                "boto3 will use the default credential chain if available."
            )

    def setup(self):
        """
        Set up logging for the S3 tools and create an S3 client using the fetched credentials.
        """
        self._setup_logging(
            "s3-tools",
            logging.INFO,
            "%(asctime)s %(name)s [%(levelname)s] %(message)s"
        )
        self._fetch_credentials()

        client_kwargs = {}
        if self.aws_access_key_id and self.aws_secret_access_key:
            client_kwargs.update(
                {
                    'aws_access_key_id': self.aws_access_key_id,
                    'aws_secret_access_key': self.aws_secret_access_key,
                }
            )

        self.s3_client = boto3.client('s3', **client_kwargs)
        

class S3PublicBuckets(S3Basics):
    """Class to check if S3 buckets are publicly accessible."""

    def check_s3_bucket_public_access(self, bucket_names_list):
        """
        Check if S3 buckets are publicly accessible.
        
        Args:
            bucket_names_list (list): List of S3 bucket names to check
        
        Returns:
            Dictionary with bucket names and their public access status
        """
        if self.logger is None or self.s3_client is None:
            self.setup()
        else:
            self._fetch_credentials()

        results = {}

        for bucket_name in bucket_names_list:
            self.logger.info("Checking public access for bucket: %s", bucket_name)
            try:
                public_access_block = self.s3_client.get_public_access_block(
                    Bucket=bucket_name
                )

                config = public_access_block.get('PublicAccessBlockConfiguration', {})
                is_public = not all(
                    config.get(flag, False)
                    for flag in (
                        'BlockPublicAcls',
                        'BlockPublicPolicy',
                        'IgnorePublicAcls',
                        'RestrictPublicBuckets',
                    )
                )

                results[bucket_name] = {
                    'is_public': is_public,
                    'status': 'FLAGGED' if is_public else 'SAFE'
                }

            except ClientError as e:
                self.logger.error("Error occurred while checking bucket %s: %s", bucket_name, e)
                results[bucket_name] = {
                    'is_public': None,
                    'status': f'ERROR: {e.response["Error"]["Code"]}'
                }

        return results
    
