import requests
from typing import List, Dict, Any
from src.utils.m_log import f_log

def _get_fallback_static_price(resource: str) -> float | str:
    """Helper to return fallback prices."""
    fallback_static = {"Front Door": 35.0, "Multi-Region App Service": 150.0}
    return fallback_static.get(resource, "Unknown")

def fetch_retail_price(resource: str) -> float | str:
    """Atomic helper satisfying Single Responsibility and 30-line max."""
    base_url = "https://prices.azure.com/api/retail/prices"
    params = {"$filter": f"serviceName eq '{resource}' and priceType eq 'Consumption'", "currencyCode": "USD"}
    
    try:
        response = requests.get(base_url, params=params, timeout=5)
        response.raise_for_status()
        items = response.json().get("Items", [])
        
        if not items:
            return _get_fallback_static_price(resource)
        return items[0].get("retailPrice", 0.0)
    except Exception as e:
        f_log(f"Cost API failure for {resource}: {e}", c_type="error")
        return "Error retrieving live price"

def calculate_cost(resources: List[str]) -> Dict[str, Any]:
    """
    Queries the live Azure Retail Prices API to establish estimated costs.
    Moves the agent from Searchbot to Financial Architect.
    """
    f_log(f"Calculating estimated costs for resources: {resources}", c_type="process")
    costs = {res: fetch_retail_price(res) for res in resources}
    return {
        "trade_off_matrix_data": costs,
        "currency": "USD",
        "billing_period": "Monthly Estimated (Base)"
    }
