from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.utils.decorators import role_required
from app.utils.db import db
from app.models.production_plan import ProductionPlan
from app.models.station import Station
from app.models.part import Part
from app.models.consumption import Consumption
from app.models.scrap import Scrap
from app.models.claim import Claim
from app.models.activity_log import ActivityLog
from app.utils.time_utils import get_thai_today
from datetime import datetime
from sqlalchemy import func

bp = Blueprint("operator", __name__, url_prefix="/operator")


@bp.route("/")
@login_required
@role_required("operator")
def index():
    today = get_thai_today()
    
    # 1. Today's Production: SUM(actual_qty) from Consumption where related ProductionPlan start_date is today
    todays_production = db.session.query(func.sum(Consumption.actual_qty)).join(
        ProductionPlan, Consumption.order_id == ProductionPlan.order_id
    ).filter(
        ProductionPlan.start_date == today
    ).scalar() or 0

    # 2. Efficiency Rate: (Actual Qty / Planned Qty) x 100 for active orders
    active_plans = ProductionPlan.query.filter_by(status="In Progress").all()
    if active_plans:
        total_planned = sum(p.quantity_planned for p in active_plans)
        total_actual = db.session.query(func.sum(Consumption.actual_qty)).filter(
            Consumption.order_id.in_([p.order_id for p in active_plans])
        ).scalar() or 0
        efficiency_rate = round((total_actual / total_planned) * 100, 1) if total_planned > 0 else 0.0
        if efficiency_rate > 100:
            efficiency_rate = 100.0
    else:
        efficiency_rate = 0.0

    # 3. Low Stock Alerts (Parts where stock < min_level)
    low_stock_alerts = Part.query.filter(
        Part.stock_qty < Part.min_level, 
        Part.is_active == 1
    ).count()

    # 4. Active Orders (ProductionPlan in progress)
    active_orders = ProductionPlan.query.filter_by(status="In Progress").count()

    # 5. Weekly Production Data (Planned vs Actual for Mon-Fri of current week)
    import datetime as dt
    weekly_labels = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    planned_data = []
    actual_data = []
    
    # Calculate start of current week (Monday)
    week_start = today - dt.timedelta(days=today.weekday())
    
    for i in range(5):
        day_date = week_start + dt.timedelta(days=i)
        
        # Planned for this day: SUM(quantity_planned)
        d_planned = db.session.query(func.sum(ProductionPlan.quantity_planned)).filter(
            ProductionPlan.start_date == day_date
        ).scalar() or 0
        planned_data.append(int(d_planned))
        
        # Actual for this day: SUM(actual_qty)
        d_start = datetime.combine(day_date, datetime.min.time())
        d_end = datetime.combine(day_date, datetime.max.time())
        d_actual = db.session.query(func.sum(Consumption.actual_qty)).filter(
            Consumption.recorded_at >= d_start,
            Consumption.recorded_at <= d_end
        ).scalar() or 0
        actual_data.append(int(d_actual))

    # 6. Part Summary (Consumption by Part Name, grouped by part_id)
    part_summary_query = db.session.query(
        Part.part_name, func.sum(Consumption.actual_qty)
    ).join(Consumption).group_by(Part.part_id, Part.part_name).limit(5).all()
    
    part_labels = [p[0][:15] + "..." if len(p[0]) > 15 else p[0] for p in part_summary_query]
    part_values = [int(p[1]) for p in part_summary_query]

    # 7. Recent Activity (Last 5 logs)
    recent_activities = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(5).all()

    return render_template(
        "operator/index.html",
        todays_production=todays_production,
        efficiency_rate=efficiency_rate,
        low_stock_alerts=low_stock_alerts,
        active_orders=active_orders,
        weekly_labels=weekly_labels,
        planned_data=planned_data,
        actual_data=actual_data,
        part_labels=part_labels,
        part_values=part_values,
        recent_activities=recent_activities
    )


@bp.route("/production")
@login_required
@role_required("operator")
def production():
    plans = ProductionPlan.query.all()
    return render_template("operator/production.html", plans=plans)


@bp.route("/api/bom/<order_id>")
@login_required
@role_required("operator")
def get_bom(order_id):
    from app.models.bom import BOM
    
    plan = ProductionPlan.query.get(order_id)
    if not plan:
        return {"bom": []}
        
    boms = BOM.query.filter_by(model=plan.product_name).all()
    data = []
    for b in boms:
        p = b.part
        status = "Adequate"
        if p.stock_qty <= 0:
            status = "Critical"
        elif p.stock_qty <= p.min_level:
            status = "Low"
            
        data.append({
            "id": p.part_id,
            "desc": p.part_name,
            "req": b.qty_per_unit,
            "unit": p.unit or "pcs",
            "stock": p.stock_qty,
            "status": status
        })
    return {"bom": data}


@bp.route("/consumption")
@login_required
@role_required("operator")
def consumption():
    order_id = request.args.get("order_id")
    plans = ProductionPlan.query.filter_by(status="In Progress").all()
    
    # Default to the first active plan if no order_id is provided
    if not order_id and plans:
        order_id = plans[0].order_id

    parts = Part.query.all()
    stations = Station.query.all()
    
    # Calculate summaries if order is selected
    total_planned = 0
    total_actual = 0
    total_scrap = 0
    records = []
    
    if order_id:
        total_planned = db.session.query(func.sum(Consumption.planned_qty)).filter_by(order_id=order_id).scalar() or 0
        total_actual = db.session.query(func.sum(Consumption.actual_qty)).filter_by(order_id=order_id).scalar() or 0
        total_scrap = db.session.query(func.sum(Scrap.scrap_qty)).join(Consumption).filter(Consumption.order_id == order_id).scalar() or 0
        records = Consumption.query.filter_by(order_id=order_id).order_by(Consumption.recorded_at.desc()).all()
        
    return render_template(
        "operator/consumption.html", 
        plans=plans, 
        parts=parts, 
        stations=stations,
        order_id=order_id,
        total_planned=total_planned,
        total_actual=total_actual,
        total_scrap=total_scrap,
        records=records
    )


@bp.route("/api/update-status", methods=["POST"])
@login_required
@role_required("operator")
def update_plan_status():
    order_id = request.json.get("order_id")
    new_status = request.json.get("status")
    
    plan = ProductionPlan.query.get(order_id)
    if not plan:
        return {"error": "Plan not found"}, 404
        
    old_status = plan.status
    plan.status = new_status
    
    # Log activity
    log = ActivityLog(
        activity_type="Status Change",
        reference_id=order_id,
        message=f"Operator changed {order_id} status from {old_status} to {new_status}",
        created_by=current_user.user_id
    )
    db.session.add(log)
    db.session.commit()
    
    return {"success": True, "new_status": new_status}


@bp.route("/submit-record", methods=["POST"])
@login_required
@role_required("operator")
def submit_record():
    order_id = request.form.get("order_id")
    part_id = request.form.get("part_id")
    station_id = request.form.get("station_id")
    actual_qty = int(request.form.get("actual_qty", 0))
    scrap_qty = int(request.form.get("scrap_qty", 0))
    claim_qty = int(request.form.get("claim_qty", 0))
    reason = request.form.get("reason", "Daily Production")

    try:
        # 1. Record Consumption
        new_cons = Consumption(
            order_id=order_id,
            part_id=part_id,
            station_id=station_id,
            actual_qty=actual_qty,
            recorded_by=current_user.user_id
        )
        db.session.add(new_cons)
        db.session.flush()

        # 2. Record Scrap if any
        if scrap_qty > 0:
            new_scrap = Scrap(
                consumption_id=new_cons.consumption_id,
                scrap_qty=scrap_qty,
                reason=reason
            )
            db.session.add(new_scrap)

        # 3. Record Claim if any
        if claim_qty > 0:
            claim_id = f"CLM-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            new_claim = Claim(
                claim_id=claim_id,
                part_id=part_id,
                qty=claim_qty,
                claim_status="Pending",
                recorded_by=current_user.user_id
            )
            db.session.add(new_claim)

        # 4. Update Stock
        part = Part.query.get(part_id)
        if part:
            part.stock_qty -= (actual_qty + scrap_qty)

        # 5. Log Activity
        if scrap_qty > 0:
            msg = f"Scrap reported: {scrap_qty} units of Part {part_id}"
            a_type = "Scrap Alert"
        else:
            msg = f"Production Entry: {actual_qty} units recorded for {order_id}"
            a_type = "Production Entry"
            
        log = ActivityLog(
            activity_type=a_type,
            reference_id=order_id,
            message=msg,
            created_by=current_user.user_id
        )
        db.session.add(log)

        db.session.commit()
        flash("Record saved successfully", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error: {str(e)}", "danger")

    return redirect(url_for("operator.consumption"))


@bp.route("/stock")
@login_required
@role_required("operator")
def stock():
    from app.models.part import Part
    
    parts = Part.query.order_by(Part.stock_qty.asc()).all()
    
    # Calculate summary counts
    critical_count = Part.query.filter(Part.stock_qty <= 0).count()
    low_count = Part.query.filter((Part.stock_qty <= Part.min_level) & (Part.stock_qty > 0)).count()
    adequate_count = Part.query.filter(Part.stock_qty > Part.min_level).count()
    
    return render_template(
        "operator/stock.html", 
        parts=parts,
        critical_count=critical_count,
        low_count=low_count,
        adequate_count=adequate_count
    )


@bp.route("/reports")
@login_required
@role_required("operator")
def reports():
    return render_template("operator/reports.html")
