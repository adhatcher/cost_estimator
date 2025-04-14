from flask import Flask, request, render_template, redirect
from decimal import Decimal
import logging
import os
from math import ceil
from calculations import read_ec2_costs, calculate_ecs_costs, calculate_eks_costs

# Set up logging  
log_level = os.getenv("LOGLEVEL", "INFO").upper()
logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)

if os.getenv("ENABLE_LOGGING", "true").lower() == "false":# Disable all logging messages
    logging.disable(logging.CRITICAL)
    logging.disable(logging.INFO)

#print(f"Enable_Logging:{os.getenv('ENABLE_LOGGING')}\t Log_Level:{log_level}")

app = Flask(__name__)

ec2_costs = read_ec2_costs()

@app.route('/')
def home():
    return redirect('/cost_estimator')

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


if __name__ == '__main__':
    app.run(host=os.getenv('FLASK_RUN_HOST', '0.0.0.0'), port=int(os.getenv('FLASK_RUN_PORT', 8000)), debug=True)
