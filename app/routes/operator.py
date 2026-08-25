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
from app.models.stock import Stock
from app.utils.time_utils import get_thai_today
from datetime import datetime
from sqlalchemy import func, or_

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
    q = (request.args.get("q") or "").strip()
    date_filter = request.args.get("date")
    page = max(request.args.get("page", 1, type=int), 1)

    query = ProductionPlan.query
    if q:
        query = query.filter(
            or_(
                ProductionPlan.order_id.ilike(f"%{q}%"),
                ProductionPlan.product_name.ilike(f"%{q}%"),
            )
        )
    if date_filter:
        try:
            parsed_date = datetime.strptime(date_filter, "%Y-%m-%d").date()
            query = query.filter(ProductionPlan.start_date == parsed_date)
        except ValueError:
            date_filter = ""

    query = query.order_by(ProductionPlan.start_date.desc(), ProductionPlan.order_id.desc())
    total = query.count()
    per_page = 12
    plans = query.limit(per_page).offset((page - 1) * per_page).all()
    total_pages = max((total + per_page - 1) // per_page, 1)

    pagination = {
        "page": page,
        "total": total,
        "total_pages": total_pages,
        "has_prev": page > 1,
        "has_next": page < total_pages,
        "prev_num": page - 1,
        "next_num": page + 1,
    }

    return render_template("operator/production.html", plans=plans, pagination=pagination, q=q, date_filter=date_filter or "")


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
            "req": b.qty_per_unit * plan.quantity_planned,
            "per_unit": b.qty_per_unit,
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
    records_page_no = max(request.args.get("records_page", 1, type=int), 1)
    plans = (
        ProductionPlan.query.filter_by(status="In Progress")
        .order_by(ProductionPlan.start_date.desc(), ProductionPlan.order_id.desc())
        .limit(30)
        .all()
    )
    
    # Default to the first active plan if no order_id is provided
    if not order_id and plans:
        order_id = plans[0].order_id

    parts = Part.query.filter_by(is_active=1).order_by(Part.part_name.asc()).limit(300).all()
    stations = Station.query.filter_by(is_active=1).order_by(Station.station_name.asc()).all()
    
    # Calculate summaries if order is selected
    total_planned = 0
    total_actual = 0
    total_scrap = 0
    records = []
    selected_plan = None

    if order_id:
        selected_plan = ProductionPlan.query.get(order_id)
        total_planned = selected_plan.quantity_planned if selected_plan else 0
        total_actual = db.session.query(func.sum(Consumption.actual_qty)).filter_by(order_id=order_id).scalar() or 0
        total_scrap = db.session.query(func.sum(Scrap.scrap_qty)).join(Consumption).filter(Consumption.order_id == order_id).scalar() or 0
        records_query = (
            Consumption.query.filter_by(order_id=order_id)
            .order_by(Consumption.recorded_at.desc())
        )
        total_records = records_query.count()
        per_page = 20
        records = records_query.limit(per_page).offset((records_page_no - 1) * per_page).all()
        records_pagination = {
            "page": records_page_no,
            "total": total_records,
            "total_pages": max((total_records + per_page - 1) // per_page, 1),
            "has_prev": records_page_no > 1,
            "has_next": records_page_no * per_page < total_records,
            "prev_num": records_page_no - 1,
            "next_num": records_page_no + 1,
        }
    else:
        records_pagination = {
            "page": 1,
            "total": 0,
            "total_pages": 1,
            "has_prev": False,
            "has_next": False,
            "prev_num": 1,
            "next_num": 1,
        }
        
    return render_template(
        "operator/consumption.html", 
        plans=plans, 
        parts=parts, 
        stations=stations,
        selected_plan=selected_plan,
        order_id=order_id,
        total_planned=total_planned,
        total_actual=total_actual,
        total_scrap=total_scrap,
        records=records,
        records_pagination=records_pagination,
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
    planned_qty = int(request.form.get("planned_qty", 0))
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
            planned_qty=planned_qty,
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

        # 4. Update Stock + Log stock_history
        part = Part.query.get(part_id)
        if part:
            total_deduct = actual_qty + scrap_qty
            part.stock_qty -= total_deduct

            # Log to stock_history (consumption deduction)
            if actual_qty > 0:
                hist_cons = Stock(
                    part_id=part_id,
                    change_qty=-actual_qty,
                    change_type="OUT",
                    reference_id=order_id,
                    created_by=current_user.user_id
                )
                db.session.add(hist_cons)

            # Log scrap deduction separately
            if scrap_qty > 0:
                hist_scrap = Stock(
                    part_id=part_id,
                    change_qty=-scrap_qty,
                    change_type="SCRAP",
                    reference_id=new_cons.consumption_id,
                    created_by=current_user.user_id
                )
                db.session.add(hist_scrap)

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

        # 6. Flash with alert metadata for sound system
        if part and scrap_qty > 0 and part.stock_qty <= part.min_level:
            flash(f"⚠️ Scrap {scrap_qty} units recorded — Part {part_id} is now LOW/CRITICAL!", "danger")
        elif scrap_qty > 0:
            flash(f"Scrap {scrap_qty} units of {part_id} recorded successfully", "warning")
        elif part and part.stock_qty <= (part.min_level or 0):
            flash(f"Record saved — ⚠️ Part {part_id} stock is LOW ({part.stock_qty} remaining)", "warning")
        else:
            flash("Record saved successfully", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Error: {str(e)}", "danger")

    return redirect(url_for("operator.consumption", order_id=order_id))



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
