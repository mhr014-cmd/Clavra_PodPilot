from openai import OpenAI
from app.config import settings

client = OpenAI(
    api_key=settings.OPENAI_API_KEY
)


async def generate_ai_insight(data: dict):

    prompt = f"""
    You are an AI manufacturing analyst.

    Analyze this ERP data:

    {data}

    Give:
    1. Production risks
    2. Shipment risks
    3. AI recommendations
    4. Bottleneck prediction

    Keep response short and professional.
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response.choices[0].message.content