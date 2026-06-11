from fastapi import APIRouter
from sqlalchemy import select, func

from app.database import AsyncSessionLocal

from app.models.production import ProductionOrder
from app.models.shipment import Shipment
from app.models.inventory import Inventory

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"]
)


# =========================
# DASHBOARD ANALYTICS
# =========================

@router.get("/dashboard")
async def dashboard_analytics():

    async with AsyncSessionLocal() as db:

        # TOTAL ORDERS
        total_orders_query = await db.execute(
            select(func.count(ProductionOrder.id))
        )

        total_orders = total_orders_query.scalar() or 0

        # RUNNING PRODUCTION
        running_query = await db.execute(
            select(func.count(ProductionOrder.id)).where(
                ProductionOrder.status.in_([
                    "Pending",
                    "Sewing",
                    "Cutting",
                    "Finishing",
                    "Packing"
                ])
            )
        )

        running_production = (
            running_query.scalar() or 0
        )

        # TOTAL SHIPMENTS
        shipment_query = await db.execute(
            select(func.count(Shipment.id))
        )

        total_shipments = (
            shipment_query.scalar() or 0
        )

        # TOTAL QUANTITY
        quantity_query = await db.execute(
            select(func.sum(ProductionOrder.quantity))
        )

        total_quantity = (
            quantity_query.scalar() or 0
        )

        # REVENUE
        estimated_revenue = total_quantity * 10

        return {

            "total_orders": total_orders,

            "running_orders": running_production,

            "total_shipments": total_shipments,

            "revenue": estimated_revenue

        }


# =========================
# INVENTORY ANALYTICS
# =========================

@router.get("/inventory")
async def inventory_analytics():

    async with AsyncSessionLocal() as db:

        inventory_query = await db.execute(
            select(Inventory)
        )

        inventory_items = (
            inventory_query.scalars().all()
        )

        # TOTAL MATERIALS
        total_materials = len(inventory_items)

        # TOTAL STOCK
        total_stock = sum([
            item.stock_qty or 0
            for item in inventory_items
        ])

        # AVAILABLE STOCK
        available_stock = sum([
            item.available_qty or 0
            for item in inventory_items
        ])

        # LOW STOCK
        low_stock = len([
            item for item in inventory_items
            if (item.available_qty or 0) < 20
        ])

        # OUT OF STOCK
        out_of_stock = len([
            item for item in inventory_items
            if (item.available_qty or 0) <= 0
        ])

        # INVENTORY VALUE
        inventory_value = total_stock * 10

        return {

            "total_materials": total_materials,

            "total_stock": total_stock,

            "available_stock": available_stock,

            "low_stock": low_stock,

            "out_of_stock": out_of_stock,

            "inventory_value": inventory_value

        }