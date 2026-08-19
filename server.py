from fastmcp import FastMCP

mcp = FastMCP("Progressive Disclosure Demo")


@mcp.tool
def get_weather(city: str) -> dict:
    """
    Get the current weather for a city.

    Use this tool when the user asks about current temperature,
    weather conditions, precipitation or general weather information.

    Args:
        city: Name of the city.

    Returns:
        Current temperature and weather condition.
    """
    return {
        "city": city,
        "temperature": 21,
        "condition": "sunny"
    }


@mcp.tool
def search_customers(query: str) -> list[dict]:
    """
    Search the customer database.

    Use this tool to find customers by their name, email address,
    company name or other identifying information.

    Args:
        query: Search term used to find matching customers.

    Returns:
        List of matching customer records.
    """
    return [
        {
            "id": 42,
            "name": "Max Mustermann",
            "company": "Example GmbH"
        }
    ]


@mcp.tool
def get_customer(customer_id: int) -> dict:
    """
    Retrieve detailed information about a specific customer.

    Args:
        customer_id: Unique numeric identifier of the customer.

    Returns:
        Complete customer record including name and company.
    """
    return {
        "id": customer_id,
        "name": "Max Mustermann",
        "company": "Example GmbH",
        "status": "active"
    }


@mcp.tool
def create_support_ticket(
    customer_id: int,
    title: str,
    description: str,
    priority: str = "normal"
) -> dict:
    """
    Create a new customer support ticket.

    Use this tool when a user wants to report an issue,
    request assistance or create a support case.

    Args:
        customer_id: Customer associated with the ticket.
        title: Short title of the problem.
        description: Detailed description of the issue.
        priority: Ticket priority such as low, normal or high.

    Returns:
        Information about the newly created support ticket.
    """
    return {
        "ticket_id": 1234,
        "customer_id": customer_id,
        "title": title,
        "priority": priority,
        "status": "open"
    }


if __name__ == "__main__":
    mcp.run(
        transport="http",
        host="127.0.0.1",
        port=8000
    )