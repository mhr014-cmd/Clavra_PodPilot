"""
AI SQL Generator — Clavra ProdPilot™
Converts natural language analytics questions into safe PostgreSQL SELECT queries.
SAFETY: SELECT only, org_id filter mandatory, LIMIT mandatory, parameterised always.
"""
import json, re
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.config import settings
from app.schemas.ai_schema import IntentResult
from app.core.constants import SQL_FORBIDDEN_KEYWORDS, SQL_MAX_ROWS

SQL_SCHEMA_CONTEXT = """
DATABASE SCHEMA for Clavra ProdPilot™ (PostgreSQL):

production_orders(id, order_no, buyer, style, quantity, status, produced_qty,
  defect_qty, line_id, org_id, created_at, updated_at, delivery_date)
  status values: Pending, Cutting, Sewing, Finishing, Packing, Completed, Cancelled

shipments(id, shipment_no, buyer, destination, carrier, status, eta,
  actual_departure, actual_arrival, org_id, created_at)
  status values: Pending, In Transit, Customs, Delivered, Delayed, Cancelled

inventory(id, material_code, material_name, category, unit, stock_qty,
  reserved_qty, available_qty, status)

production_lines(id, line_name, supervisor, status, target_output,
  actual_output, efficiency, defects, operators)

STRICT RULES:
1. Return ONLY a SELECT statement
2. ALWAYS include WHERE org_id = :org_id
3. ALWAYS add LIMIT :limit
4. Use :param_name for ALL variable values — never inline user values
5. No semicolons at end
6. Only SELECT — no INSERT/UPDATE/DELETE/DROP

Return ONLY JSON: {"sql": "...", "params": {"key": "value"}, "explanation": "..."}
"""

SUMMARY_PROMPT = """You are a data analyst. Given a SQL query result, write a clear 1-3 sentence 
natural language summary. Be specific — include numbers. Do not say "the data shows"."""


async def generate_and_execute_sql(
    question: str,
    intent: IntentResult,
    org_id: int,
    db: AsyncSession,
) -> dict:
    """Full pipeline: question → SQL → validate → execute → summarise."""

    # Step 1: Generate SQL
    sql_data = await _generate_sql(question, intent)
    sql = sql_data["sql"]
    params = sql_data.get("params", {})

    # Step 2: Safety validation
    is_safe, reason = _validate_sql(sql)
    if not is_safe:
        raise ValueError(f"SQL safety check failed: {reason}")

    # Step 3: Inject mandatory params
    params["org_id"] = org_id
    params["limit"] = min(int(params.get("limit", 100)), SQL_MAX_ROWS)

    # Step 4: Execute
    result = await db.execute(text(sql), params)
    rows = [dict(row._mapping) for row in result.fetchall()]

    # Step 5: Summarise
    summary = await _summarise_results(question, rows, sql)

    return {"sql": sql, "rows": rows, "summary": summary, "row_count": len(rows)}


_PLACEHOLDER_KEYS = {"sk-your-openai-key-here", "sk-xxxx", "sk-placeholder", ""}


async def _generate_sql(question: str, intent: IntentResult) -> dict:
    """Use GPT-4o to generate SQL from the question."""
    key = (settings.OPENAI_API_KEY or "").strip()
    if not (key.startswith("sk-") and key not in _PLACEHOLDER_KEYS):
        raise ValueError(
            "SQL analytics require an OpenAI API key. "
            "Add OPENAI_API_KEY=sk-... to backend/.env to enable this feature."
        )

    prompt = f"{SQL_SCHEMA_CONTEXT}\n\nQuestion: {question}\nIntent: {intent.intent}\nEntities: {intent.entities}"

    if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.startswith("sk-"):
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a PostgreSQL expert. Return only JSON."},
                {"role": "user",   "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=500,
        )
        return json.loads(response.choices[0].message.content)
    else:
        from app.ai.ollama_service import ask_ollama
        raw = await ask_ollama(f"Generate SQL JSON. {prompt}")
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError("Could not parse SQL from AI response")


def _validate_sql(sql: str) -> tuple[bool, str]:
    """Safety validator — must pass before any execution."""
    sql_upper = sql.upper().strip()

    # Must be SELECT
    if not sql_upper.startswith("SELECT"):
        return False, "Only SELECT statements are allowed"

    # No write keywords
    for kw in SQL_FORBIDDEN_KEYWORDS:
        pattern = rf'\b{kw}\b'
        if re.search(pattern, sql_upper):
            return False, f"Forbidden keyword: {kw}"

    # Must have org_id param
    if ":org_id" not in sql:
        return False, "Query must include WHERE org_id = :org_id"

    # Must have LIMIT
    if "LIMIT" not in sql_upper:
        return False, "Query must include a LIMIT clause"

    # No semicolons
    if ";" in sql:
        return False, "Semicolons not allowed"

    return True, "OK"


async def _summarise_results(question: str, rows: list, sql: str) -> str:
    """Convert raw query results to natural language."""
    if not rows:
        return "No data found for your query."

    row_preview = str(rows[:10])

    if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.startswith("sk-"):
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SUMMARY_PROMPT},
                {"role": "user",   "content": f"Question: {question}\nRows returned: {len(rows)}\nData sample: {row_preview}"}
            ],
            temperature=0.3,
            max_tokens=200,
        )
        return response.choices[0].message.content.strip()

    # Simple fallback
    if len(rows) == 1 and len(rows[0]) == 1:
        val = list(rows[0].values())[0]
        return f"The result is: **{val}**"
    return f"Found {len(rows)} record(s) matching your query."
