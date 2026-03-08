import requests
import logging
from typing import List, Dict, Any

def calculate_cost(resources: List[str]) -> Dict[str, Any]:
    """
    Queries the live Azure Retail Prices API to establish estimated costs.
    Moves the agent from Searchbot to Financial Architect.
    """
    logging.info(f"Calculating estimated costs for resources: {resources}")
    
    # Base URL for the Azure Retail Prices API
    base_url = "https://prices.azure.com/api/retail/prices"
    
    costs = {}
    
    for resource in resources:
        try:
             # A simplistic generic query. In reality, this requires complex OData filtering 
             # (e.g., specific ARM region, currency, tier)
             params = {
                 "$filter": f"serviceName eq '{resource}' and priceType eq 'Consumption'",
                 "currencyCode": "USD"
             }
             
             # Standard Library First (Requests is an industry standard external, but we keep the parsing native).
             response = requests.get(base_url, params=params, timeout=5)
             response.raise_for_status()
             
             data = response.json()
             items = data.get("Items", [])
             
             if items:
                 # Just taking the first returned standard retail price
                 costs[resource] = items[0].get("retailPrice", 0.0)
             else:
                 # Fallback static dictionary if the live API doesn't find the exact broad match
                 fallback_static = {
                     "Front Door": 35.0,
                     "Multi-Region App Service": 150.0
                 }
                 costs[resource] = fallback_static.get(resource, "Unknown")
                 
        except Exception as e:
             logging.error(f"Cost API failure for {resource}: {e}")
             costs[resource] = "Error retrieving live price"
             
    return {
        "trade_off_matrix_data": costs,
        "currency": "USD",
        "billing_period": "Monthly Estimated (Base)"
    }
