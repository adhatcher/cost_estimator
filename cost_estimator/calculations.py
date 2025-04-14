import logging
import csv
from math import ceil
from decimal import Decimal
import os

# Set up logging  
log_level = os.getenv("LOGLEVEL", "INFO").upper()
logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)

if os.getenv("ENABLE_LOGGING", "true").lower() == "false":# Disable all logging messages
    logging.disable(logging.CRITICAL)
    logging.disable(logging.INFO)

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
