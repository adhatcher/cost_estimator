from flask import Flask, request, render_template, jsonify
from decimal import Decimal
import csv
import json
# import subprocess
# import datetime
import logging
import boto3
import os
from botocore.exceptions import BotoCoreError, ClientError
from math import ceil

log_level = os.getenv("LOGLEVEL", "INFO").upper()
logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)

if os.getenv("ENABLE_LOGGING", "true").lower() == "false":# Disable all logging messages
    logging.disable(logging.CRITICAL)
    logging.disable(logging.INFO)

print(f"Enable_Logging:{os.getenv('ENABLE_LOGGING')}\t Log_Level:{log_level}")
app = Flask(__name__)

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

ec2_costs = []

def read_ec2_costs(file_path='cost_estimator/static/ec2_costs.csv'):
    ec2_costs = []
    try:
        with open(file_path, mode='r') as csv_file:
            csv_reader = csv.DictReader(csv_file, delimiter=',')  # Updated to use comma as delimiter
            headers = csv_reader.fieldnames
            if headers and len(headers) == 1 and ',' in headers[0]:
                # Handle malformed headers where all data is in a single key
                logger.error(f"Malformed CSV headers: {headers}. Check the delimiter.")
                return []
            logger.debug(f"CSV Headers: {headers}")  # Log the headers for debugging
            for row in csv_reader:
                ec2_costs.append(row)
    except FileNotFoundError:
        logger.error(f"Error: File {file_path} not found.")
        exit(103)
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
    return ec2_costs

ec2_costs = read_ec2_costs()

@app.route('/cost_estimator', methods=['GET', 'POST'])
def cost_estimator():
    if request.method == 'POST':
        # Validate and collect parameters
        try:
            try:
                pod_cpu = Decimal(request.form['pod_cpu'])
            except ValueError:
                pod_cpu = Decimal(0)
            try:   
                pod_mem = Decimal(request.form['pod_mem'])
            except ValueError:     
                pod_mem = Decimal(0)
            try:
                peak_pods = int(request.form['peak_pods'])
            except ValueError:
                peak_pods = 0
            try:
                peak_hours = int(request.form['peak_hours'])
            except (ValueError, TypeError):
                peak_hours = 0
            try:
                normal_pods = int(request.form.get('normal_pods', 0))
            except ValueError:
                normal_pods = 0
            try:    
                normal_hours = int(request.form.get('normal_hours', 0))
            except ValueError:
                normal_hours = 0
            try:
                off_hours_pods = int(request.form.get('off_hours_pods', 0))
            except ValueError:
                off_hours_pods = 0  # Fallback to a default value
            try:
                off_hours = int(request.form.get('off_hours', 0))
            except ValueError:
                off_hours = 0
        except (ValueError, KeyError) as e:
            logger.error(f"Error in input validation: {e}")
            return "Invalid input", 400

        # Redirect to display_costs API
        try:
            return display_costs(pod_cpu, pod_mem, peak_pods, peak_hours, normal_pods, normal_hours, off_hours_pods, off_hours)
        except Exception as e:
            logger.error(f"Error while calculating costs: {e}")
            return "An error occurred while processing your request. Please try again later.", 500
    return render_template('cost_estimator.html')

@app.route('/display_costs', methods=['POST'])
def display_costs(pod_cpu, pod_mem, peak_pods, peak_hours, normal_pods, normal_hours, off_hours_pods, off_hours):
    # Call calculate_eks_costs and calculate_ecs_costs
    try:
        eks_data = calculate_eks_costs(pod_cpu, pod_mem, peak_pods, peak_hours, normal_pods, normal_hours, off_hours_pods, off_hours)
        ecs_data = calculate_ecs_costs(pod_cpu, pod_mem, peak_pods, peak_hours, normal_pods, normal_hours, off_hours_pods, off_hours)
    except Exception as e:
        logger.error(f"Error while calculating costs in display_costs: {e}")
        return "An error occurred while calculating costs. Please check the input and try again.", 500
    param_data = ({
        "pod_cpu": pod_cpu,
        "pod_mem": pod_mem,
        "peak_pods": peak_pods,
        "peak_hours": peak_hours,
        "normal_pods": normal_pods,
        "normal_hours": normal_hours,
        "off_hours_pods": off_hours_pods,
        "off_hours": off_hours
    })

    # Render results
    return render_template('display_costs.html', eks_data=eks_data, ecs_data=ecs_data, param_data=param_data)


def calculate_ecs_costs(pod_cpu, pod_mem, peak_pods, peak_hours, normal_pods, normal_hours, off_hours_pods, off_hours):
    # ecs_pricing = ECS_PRICING()
    # creds = ecs_pricing.get_aws_session_token() 
    # cpu = ecs_pricing.fetch_ecs_cpu_pricing(creds)
    # mem = ecs_pricing.fetch_ecs_mem_pricing(creds)   
    
    ecs_vcpu_pricing = 0.03238
    ecs_mem_pricing = 0.00356
    cpu = Decimal(ecs_vcpu_pricing)
    mem = Decimal(ecs_mem_pricing)


    peak_charges = (cpu * pod_cpu + mem * pod_mem) * peak_pods * peak_hours * 30
    normal_charges = (cpu * pod_cpu + mem * pod_mem) * normal_pods * normal_hours * 30
    off_hours_charges = (cpu * pod_cpu + mem * pod_mem) * off_hours_pods * off_hours * 30

    return {
        "peak_hours": peak_charges,
        "normal_hours": normal_charges,
        "off_hours": off_hours_charges,
        "total": peak_charges + normal_charges + off_hours_charges
    }


def get_eks_costs(pod_cpu, pod_mem, pods, hours):
    
    global ec2_costs
    cheapest_cost = None

    for ec2 in ec2_costs:
        try:
            type = ec2['Instance_Type']  # Updated to match actual CSV header
            rate = Decimal(ec2.get('Rate', 4))  # Safely access 'Rate' with a default value
            vcpu = Decimal(ec2['vCPU'])  # Ensure 'vCPU' matches the actual CSV header
            memory = Decimal(ec2['Memory'])  # Ensure 'Memory' matches the actual CSV header
            
            if Decimal(pod_cpu) > vcpu or Decimal(pod_mem) > memory:
                logger.debug(f"Skipping {type}: pod_cpu ({pod_cpu}) > vcpu ({vcpu}) or pod_mem ({pod_mem}) > memory ({memory})")
                continue  # Skip this row if pod_cpu > vcpu or pod_mem > memory
            
            # Peak nodes calculation
            # Calculate the number of nodes required based on CPU and memory
            cpu_nodes = ceil(pods / (vcpu / Decimal(pod_cpu)))  # Convert pod_cpu to Decimal
            mem_nodes = ceil(pods / (memory / Decimal(pod_mem)))  # Convert pod_mem to Decimal
            nodes = max(max(cpu_nodes, mem_nodes), 1)
            
            # Calculate total cost
            cost = rate * nodes * hours

            # Update cheapest option
            if cheapest_cost is None or cost < cheapest_cost:
                cheapest_cost = cost
                cheapest_option = {
                    "type": ec2['Instance_Type'],  # Updated to match actual CSV header
                    "rate": rate,
                    "nodes": nodes,
                    "total_cost": cost
                }
            logger.info(f"{type}:({vcpu}x{memory})\t\t {rate}\t\t {cpu_nodes}\t {mem_nodes}\t\t {nodes}\t {cost}")

        except KeyError as e:
            logger.error(f"Missing key in EC2 data: {e}. EC2 entry: {ec2}")
            continue
        except (ValueError, Exception) as e:
            logger.error(f"Error processing EC2 data: {e}. EC2 entry: {ec2}")
            continue
    
    logger.info(f"Cheapest costs: {cheapest_cost}")
    return cheapest_cost


def calculate_eks_costs(pod_cpu, pod_mem, peak_pods, peak_hours, normal_pods, normal_hours, off_hours_pods, off_hours):
     
    logger.info(f"peak_pods: {peak_pods}, pod_cpu: {pod_cpu}, pod_mem: {pod_mem}")
    logger.info(f"Instance type\t\t\t rate\t cpu_nodes\t mem_nodes\t nodes\t cost")

    peak_charges = get_eks_costs(pod_cpu, pod_mem, peak_pods, peak_hours) * 30
    normal_charges = get_eks_costs(pod_cpu, pod_mem, normal_pods, normal_hours) * 30
    off_hours_charges = get_eks_costs(pod_cpu, pod_mem, off_hours_pods, off_hours) * 30
    logger.info(f"Peak costs: {peak_charges}")
    logger.info(f"Normal costs: {normal_charges}") 
    logger.info(f"Off costs: {off_hours_charges}")
    
    control_plane = Decimal(0.10) * (peak_hours + normal_hours + off_hours) *30
    core_nodes = next((Decimal(ec2['Rate']) * 4 * (peak_hours + normal_hours + off_hours) 
                       for ec2 in ec2_costs if ec2['Instance_Type'] == 'm5a.2xlarge'), Decimal(0)) * 30
    
    total_charges = peak_charges + normal_charges + off_hours_charges + control_plane + core_nodes
    logger.info(f"Total costs: {total_charges}")
    # Return the total costs for peak, normal, and off hours


    return {
        "peak_hours": peak_charges,
        "normal_hours": normal_charges,
        "off_hours": off_hours_charges,
        "control_plane": control_plane,
        "core_nodes": core_nodes,
        "total": total_charges
    }


if __name__ == '__main__':
    app.run(host=os.getenv('FLASK_RUN_HOST', '0.0.0.0'), port=int(os.getenv('FLASK_RUN_PORT', 8000)), debug=True)
