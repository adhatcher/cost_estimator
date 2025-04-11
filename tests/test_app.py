import pytest
from flask import Flask
from cost_estimator.app import app, calculate_eks_costs, calculate_ecs_costs

@pytest.fixture
def client():
    app.testing = True
    with app.test_client() as client:
        yield client

# Test cases for /calculate endpoint
def test_calculate_endpoint(client):
    response = client.post('/calculate', json={'quantity': 10, 'price_per_unit': 5})
    assert response.status_code == 200
    assert response.get_json() == {'total_cost': 50}

def test_calculate_endpoint_invalid_input(client):
    response = client.post('/calculate', json={'quantity': -10, 'price_per_unit': 5})
    assert response.status_code == 400
    assert 'error' in response.get_json()

# Test cases for /ecs-prices endpoint
def test_ecs_prices_endpoint_valid(client, mocker):
    mocker.patch('cost_estimator.ecs_price_downloads.fetch_ecs_prices', return_value='{"prices": {"instance_type": "t2.micro", "price": 0.0116}}')
    mocker.patch('cost_estimator.ecs_price_downloads.parse_ecs_prices', return_value={"instance_type": "t2.micro", "price": 0.0116})
    response = client.get('/ecs-prices?url=https://example.com/prices')
    assert response.status_code == 200
    assert response.get_json() == {"instance_type": "t2.micro", "price": 0.0116}

def test_ecs_prices_endpoint_invalid_url(client, mocker):
    mocker.patch('cost_estimator.ecs_price_downloads.fetch_ecs_prices', side_effect=Exception("Invalid URL"))
    response = client.get('/ecs-prices?url=https://invalid-url.com')
    assert response.status_code == 400
    assert 'error' in response.get_json()

# Test cases for /cost_estimator endpoint
def test_cost_estimator_get(client):
    response = client.get('/cost_estimator')
    assert response.status_code == 200  # Ensure the GET request renders the form

def test_cost_estimator_post_valid(client, mocker):
    mocker.patch('cost_estimator.app.display_costs', return_value="Mocked Display Costs")
    response = client.post('/cost_estimator', data={
        'pod_cpu': '0.5',
        'pod_mem': '512',
        'peak_pods': '10',
        'peak_hours': '5',
        'normal_pods': '5',
        'normal_hours': '10',
        'off_hours_pods': '2',
        'off_hours': '8'
    })
    assert response.status_code == 200
    assert response.data.decode() == "Mocked Display Costs"

def test_cost_estimator_post_invalid(client):
    response = client.post('/cost_estimator', data={
        'pod_cpu': 'invalid',
        'pod_mem': '512',
        'peak_pods': '10',
        'peak_hours': '5'
    })
    assert response.status_code == 400  # Invalid input should return 400

# Test cases for calculate_eks_costs
def test_calculate_eks_costs():
    result = calculate_eks_costs(0.5, 512, 10, 5, 5, 10, 2, 8)
    assert result == {
        "peak_hours": 0,
        "normal_hours": 0,
        "off_hours": 0,
        "control_plane": 0,
        "core_node": 0,
        "total": 0
    }  # Placeholder logic, adjust as needed

# Test cases for calculate_ecs_costs
def test_calculate_ecs_costs(mocker):
    mocker.patch('cost_estimator.ecs_price_downloads.get_ecs_cpu_pricing', return_value=0.02)
    mocker.patch('cost_estimator.ecs_price_downloads.get_ecs_mem_pricing', return_value=0.01)
    result = calculate_ecs_costs(0.5, 512, 10, 5, 5, 10, 2, 8)
    assert result == {
        "peak_hours": (0.02 * 0.5 + 0.01 * 512) * 10 * 5,
        "normal_hours": (0.02 * 0.5 + 0.01 * 512) * 5 * 10,
        "off_hours": (0.02 * 0.5 + 0.01 * 512) * 2 * 8,
        "total": ((0.02 * 0.5 + 0.01 * 512) * 10 * 5) +
                 ((0.02 * 0.5 + 0.01 * 512) * 5 * 10) +
                 ((0.02 * 0.5 + 0.01 * 512) * 2 * 8)
    }

# Test cases for /display_costs endpoint
def test_display_costs(client, mocker):
    mocker.patch('cost_estimator.app.calculate_eks_costs', return_value={"total": 100})
    mocker.patch('cost_estimator.app.calculate_ecs_costs', return_value={"total": 200})
    response = client.post('/display_costs', json={
        'pod_cpu': 0.5,
        'pod_mem': 512,
        'peak_pods': 10,
        'peak_hours': 5,
        'normal_pods': 5,
        'normal_hours': 10,
        'off_hours_pods': 2,
        'off_hours': 8
    })
    assert response.status_code == 200
    assert b'display_costs.html' in response.data  # Ensure the template is rendered