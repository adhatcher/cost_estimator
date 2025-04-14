import boto3
import json
import logging
from botocore.exceptions import BotoCoreError, ClientError
from decimal import Decimal
from math import ceil

# To be used with app.py if you want to dynamically call the pricing API to get the pricing for ecs.

class ECS_PRICING:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def get_aws_session_token(self, duration_seconds=3600):
        """Uses boto3 to call `sts get-session-token` and returns parsed credentials."""
        try:
            sts_client = boto3.client('sts', region_name='us-east-1')
            response = sts_client.get_session_token(DurationSeconds=duration_seconds)
            credentials = response.get("Credentials", {})
            return {
                "AccessKeyId": credentials.get("AccessKeyId"),
                "SecretAccessKey": credentials.get("SecretAccessKey"),
                "SessionToken": credentials.get("SessionToken")
            }
        except (BotoCoreError, ClientError) as error:
            self.logger.exception(f"Error fetching AWS session token: {error}")
            return None

    def fetch_ecs_cpu_pricing(self, creds=None):
        if not creds:
            self.logger.debug("Calling get_aws_session_token")
            credentials = self.get_aws_session_token()
        else:
            self.logger.debug("Using passed creds")
            credentials = creds

        access_key_id = credentials['AccessKeyId']
        secret_access_key = credentials['SecretAccessKey']
        session_token = credentials['SessionToken']

        try:
            pricing_client = boto3.client(
                'pricing',
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
                aws_session_token=session_token,
                region_name='us-east-1'
            )

            cpu_filters = [
                {"Type": "TERM_MATCH", "Field": "servicecode", "Value": "AmazonECS"},
                {"Type": "TERM_MATCH", "Field": "regionCode", "Value": "us-east-1"},
                {"Type": "TERM_MATCH", "Field": "cpuArchitecture", "Value": "ARM"},
                {"Type": "TERM_MATCH", "Field": "resource", "Value": "per vCPU per hour"}
            ]

            response = pricing_client.get_products(
                ServiceCode='AmazonECS',
                Filters=cpu_filters,
                FormatVersion='aws_v1'
            )

            cpu_price_list = response.get('PriceList', [])
            if not cpu_price_list:
                self.logger.exception("Warning: Price list is empty. Verify filters and API configuration.")

            cpu_price = json.loads(cpu_price_list[0])['terms']['OnDemand']
            cpu_price = next(iter(cpu_price.values()))['priceDimensions']
            cpu_price = next(iter(cpu_price.values()))['pricePerUnit']['USD']

            self.logger.info(f"CPU PRICE = {cpu_price}\n")
            return Decimal(cpu_price)

        except (BotoCoreError, ClientError) as error:
            self.logger.exception(f"Error fetching ECS CPU pricing: {error}")
            raise Exception(f"Error fetching ECS CPU pricing: {error}")

    def fetch_ecs_mem_pricing(self, creds=None):
        if not creds:
            self.logger.debug("Calling get_aws_session_token")
            credentials = self.get_aws_session_token()
        else:
            self.logger.debug("Using passed creds")
            credentials = creds

        access_key_id = credentials['AccessKeyId']
        secret_access_key = credentials['SecretAccessKey']
        session_token = credentials['SessionToken']

        try:
            pricing_client = boto3.client(
                'pricing',
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
                aws_session_token=session_token,
                region_name='us-east-1'
            )

            filters = [
                {"Type": "TERM_MATCH", "Field": "servicecode", "Value": "AmazonECS"},
                {"Type": "TERM_MATCH", "Field": "regionCode", "Value": "us-east-1"},
                {"Type": "TERM_MATCH", "Field": "cpuArchitecture", "Value": "ARM"},
                {"Type": "TERM_MATCH", "Field": "memorytype", "Value": "perGB"}
            ]

            response = pricing_client.get_products(
                ServiceCode='AmazonECS',
                Filters=filters,
                FormatVersion='aws_v1'
            )

            memory_price_list = response.get('PriceList', [])
            if not memory_price_list:
                self.logger.debug("Warning: Price list is empty. Verify filters and API configuration.")

            memory_price = json.loads(memory_price_list[0])['terms']['OnDemand']
            memory_price = next(iter(memory_price.values()))['priceDimensions']
            memory_price = next(iter(memory_price.values()))['pricePerUnit']['USD']

            self.logger.info(f"MEMORY PRICE = {memory_price}\n")
            return Decimal(memory_price)

        except (BotoCoreError, ClientError) as error:
            self.logger.exception(f"Error fetching ECS Memory pricing: {error}")
            raise Exception(f"Error fetching ECS Memory pricing: {error}")
