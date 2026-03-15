# ไฟล์นี้คือ "สมองส่วนกลางของ Admin" ครับ จัดการทุกอย่างที่แอดมินต้องเห็นและทำ
# ทำไมถึงมีไฟล์นี้? -> เพื่อรวมศูนย์การจัดการข้อมูลระดับสูง เช่น การดูภาพรวม (Dashboard), การคีย์ข้อมูลสต็อกแบบ Manual และกำรออกรายงาน
# มีการเรียกใช้อะไรบ้าง?
# - Models: ดึงข้อมูลจากเกือบทุก Model (Part, Consumption, Plan, BOM) มาคำนวณเป็น KPI
# - Pandas & Openpyxl: ใช้สำหรับอ่านและสร้างไฟล์ Excel (ทั้งตอน Import ข้อมูลจากโรงงาน และ Export รายงานออกไป)
# - Decorators (@role_required): เพื่อรักษาความปลอดภัย ให้เฉพาะคนที่มีสิทธิ์ Admin เท่านั้นที่เข้าหน้านี้ได้
# ที่เขียนแบบนี้เพราะเราต้องการให้ Admin มีอำนาจสูงสุดในการควบคุมและตรวจสอบข้อมูลทั้งหมดจากจุดเดียวครับ

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_file,
)
import pandas as pd
import io
from datetime import datetime
from flask_login import login_required
from app.utils.decorators import role_required
from app.utils.db import db

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/")
@login_required
@role_required("admin")
def index():
    from app.models.part import Part
    from app.models.consumption import Consumption
    from app.models.bom import BOM
    from app.models.scrap import Scrap
    from app.models.activity_log import ActivityLog
    from sqlalchemy import func

    # 1. KPI Stats
    # Total units in inventory (using stock_qty)
    total_parts_units = db.session.query(func.sum(Part.current_stock)).scalar() or 0
    # Number of SKUs low on stock (using min_level)
    low_stock_count = Part.query.filter(
        Part.current_stock <= Part.min_stock_level
    ).count()

    # Total scrap units (from scrap table)
    scrap_count = db.session.query(func.sum(Scrap.scrap_qty)).scalar() or 0

    # 2. Critical Alerts & Activity Feed
    alerts = []
    # Identify critical items
    critical_items = (
        Part.query.filter(Part.current_stock < (Part.min_stock_level / 2))
        .limit(3)
        .all()
    )
    
    for item in critical_items:
        alerts.append({
            "level": "CRITICAL",
            "title": "Stock Alert",
            "message": f"{item.name} ({item.id}): Critical stock ({item.current_stock} {item.unit})",
            "time": "Recent"
        })

    # Get recent activity logs
    recent_activities = ActivityLog.query.order_by(ActivityLog.id.desc()).limit(5).all()
    activity_feed = []
    for log in recent_activities:
        activity_feed.append({
            "type": log.activity_type,
            "message": log.message,
            "time": log.created_at.strftime("%H:%M")
        })

    # 3. Inventory & Usage Overview
    inventory_usage = []
    parts = Part.query.order_by(Part.current_stock.asc()).limit(10).all()

    for p in parts:
        # Sum of consumption
        actual_used = db.session.query(func.sum(Consumption.actual_qty)).filter_by(part_id=p.id).scalar() or 0
        
        # Calculate scrap for this part
        scrap_qty = (
            db.session.query(func.sum(Scrap.scrap_qty))
            .join(Consumption)
            .filter(Consumption.part_id == p.id)
            .scalar() or 0
        )

        # Planned from BOM
        required_qty = (
            db.session.query(func.sum(BOM.quantity_required))
            .join(Part)
            .filter(Part.id == p.id)
            .scalar() or 0
        )

        status = "OK"
        if p.current_stock == 0:
            status = "CRITICAL"
        elif p.current_stock <= p.min_stock_level:
            status = "Low Stock"

        inventory_usage.append({
            "name": p.name,
            "sku": p.id,
            "required_qty": required_qty,
            "actual_used": actual_used,
            "scrap": scrap_qty,
            "remaining_stock": p.current_stock,
            "status": status,
        })

    # 4. Chart Data
    top_consumed = (
        db.session.query(Part.name, func.sum(Consumption.actual_qty).label("total"))
        .join(Consumption)
        .group_by(Part.id)
        .order_by(db.desc("total"))
        .limit(6)
        .all()
    )

    chart_data = {
        "labels": [r[0] for r in top_consumed] if top_consumed else ["No Data"],
        "actual": [int(r[1]) for r in top_consumed] if top_consumed else [0],
        "planned": [0] * len(top_consumed) if top_consumed else [0]
    }

    return render_template(
        "admin/dashboard.html",
        total_parts=total_parts_units,
        low_stock_count=low_stock_count,
        scrap_count=scrap_count,
        active_alerts=len(alerts),
        alerts=alerts,
        activity_feed=activity_feed,
        inventory_usage=inventory_usage,
        chart_data=chart_data,
    )


@bp.route("/data-entry")
@login_required
@role_required("admin")
def data_entry():
    from app.models.station import Station
    from app.models.part import Part

    stations = Station.query.all()
    parts = Part.query.all()
    return render_template("admin/data_entry.html", stations=stations, parts=parts)


@bp.route("/submit-data", methods=["POST"])
@login_required
@role_required("admin")
def submit_data():
    from app.models.consumption import Consumption
    from app.models.production_plan import ProductionPlan
    from app.models.part import Part
    from app.models.activity_log import ActivityLog
    from flask_login import current_user

    station_id = request.form.get("station_id")
    part_id = request.form.get("part_id")
    quantity_used = int(request.form.get("quantity_used", 0))
    scrap_qty = int(request.form.get("scrap_qty", 0))

    # Logic: Find an active production plan
    plan = ProductionPlan.query.filter_by(status="In Progress").first()
    if not plan:
        flash("No active production plan found.", "danger")
        return redirect(url_for("admin.data_entry"))

    new_consumption = Consumption(
        order_id=plan.order_id,
        part_id=part_id,
        station_id=station_id,
        actual_qty=quantity_used,
        recorded_by=current_user.id
    )

    # Update part stock
    part = Part.query.get(part_id)
    if part:
        part.current_stock -= (quantity_used + scrap_qty)
        
    db.session.add(new_consumption)
    db.session.flush() # Get consumption ID for scrap

    if scrap_qty > 0:
        from app.models.scrap import Scrap
        new_scrap = Scrap(
            consumption_id=new_consumption.id,
            scrap_qty=scrap_qty,
            reason="Manual Entry"
        )
        db.session.add(new_scrap)

    # Log activity
    log = ActivityLog(
        activity_type="Data Entry",
        reference_id=plan.order_id,
        message=f"Admin recorded {quantity_used} units for {part.id}",
        created_by=current_user.id
    )
    db.session.add(log)
    
    db.session.commit()

    flash("Data recorded successfully!", "success")
    return redirect(url_for("admin.data_entry"))


@bp.route("/upload-excel", methods=["POST"])
@login_required
@role_required("admin")
def upload_excel():
    if "excel_file" not in request.files:
        flash("No file part", "danger")
        return redirect(url_for("admin.data_entry"))

    file = request.files["excel_file"]
    if file.filename == "":
        flash("No selected file", "danger")
        return redirect(url_for("admin.data_entry"))

    try:
        df = pd.read_excel(file)
        from app.models.station import Station
        from app.models.part import Part
        from app.models.consumption import Consumption
        from app.models.production_plan import ProductionPlan
        from app.models.scrap import Scrap
        from app.models.activity_log import ActivityLog
        from flask_login import current_user

        success_count = 0
        for _, row in df.iterrows():
            station = Station.query.filter_by(
                name=str(row["StationName"]).strip()
            ).first()
            part = Part.query.filter_by(id=str(row["PartSKU"]).strip()).first()

            if station and part:
                # Find active plan
                plan = ProductionPlan.query.filter_by(status="In Progress").first()
                if not plan:
                    plan = ProductionPlan.query.order_by(ProductionPlan.order_id.desc()).first()

                if plan:
                    qty = int(row["QuantityUsed"])
                    scrap_qty = int(row.get("ScrapQty", 0))

                    cons = Consumption(
                        station_id=station.id,
                        part_id=part.id,
                        order_id=plan.order_id,
                        actual_qty=qty,
                        recorded_by=current_user.id
                    )
                    db.session.add(cons)
                    db.session.flush()

                    if scrap_qty > 0:
                        new_scrap = Scrap(
                            consumption_id=cons.id,
                            scrap_qty=scrap_qty,
                            reason="Excel Upload"
                        )
                        db.session.add(new_scrap)
                    
                    part.current_stock -= (qty + scrap_qty)
                    success_count += 1

        if success_count > 0:
            log = ActivityLog(
                activity_type="Excel Import",
                message=f"Imported {success_count} records via Excel",
                created_by=current_user.id
            )
            db.session.add(log)
            db.session.commit()
            flash(f"Successfully processed {success_count} records from Excel!", "success")
        else:
            flash("No matching records found in Excel.", "warning")

    except Exception as e:
        db.session.rollback()
        flash(f"Error processing Excel: {str(e)}", "danger")

    return redirect(url_for("admin.data_entry"))


@bp.route("/download-template")
@login_required
@role_required("admin")
def download_template():
    # Generate a simple buffer for Excel
    output = io.BytesIO()
    df = pd.DataFrame(columns=["StationName", "PartSKU", "QuantityUsed", "ScrapQty"])
    # Add dummy data
    df.loc[0] = ["Station A", "M-401", 10, 1]

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Template")

    output.seek(0)
    return send_file(
        output,
        download_name="data_entry_template.xlsx",
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@bp.route("/production")
@login_required
@role_required("admin")
def production():
    from app.models.production_plan import ProductionPlan
    from app.models.bom import BOM
    from app.models.consumption import Consumption
    from sqlalchemy import func

    # Find the active 'In Progress' plan
    plan = ProductionPlan.query.filter_by(status="In Progress").first()
    if not plan:
        plan = ProductionPlan.query.order_by(ProductionPlan.order_id.desc()).first()

    bom_items = []
    total_part_types = 0
    total_items_required = 0

    if plan:
        # Get BOM for this plan's product model
        boms = BOM.query.filter_by(model=plan.product_name).all()
        total_part_types = len(boms)

        for b in boms:
            part = b.part
            qty_per_unit = b.quantity_required
            calculated_required = qty_per_unit * plan.planned_qty
            total_items_required += calculated_required

            # Get actual consumption for this part in this plan
            actual_used = db.session.query(func.sum(Consumption.actual_qty)).filter_by(
                order_id=plan.order_id, part_id=b.part_id
            ).scalar() or 0

            bom_items.append({
                "part_code": part.id,
                "part_name": part.name,
                "qty_per_unit": round(qty_per_unit, 2),
                "unit": part.unit or "pcs",
                "calculated_required": calculated_required,
                "actual_used": actual_used,
                "percentage": round((actual_used / calculated_required * 100), 1) if calculated_required > 0 else 0
            })

    shift_info = "Day Shift (06:00 - 18:00)"
    product_name = plan.product_name if plan else "N/A"

    return render_template(
        "admin/production.html",
        plan=plan,
        bom_items=bom_items,
        total_part_types=total_part_types,
        total_items_required=total_items_required,
        shift_info=shift_info,
        product_name=product_name,
    )


@bp.route("/consumption")
@login_required
@role_required("admin")
def consumption():
    return render_template("admin/consumption.html")


@bp.route("/stock")
@login_required
@role_required("admin")
def stock():
    from app.models.part import Part
    from app.models.stock import Stock
    from app.models.claim import Claim

    # 1. Main Inventory Table
    inventory = Part.query.order_by(Part.current_stock.asc()).all()

    # 2. Recent Stock History (IN/OUT)
    history = Stock.query.order_by(Stock.id.desc()).limit(20).all()

    # 3. Pending & Recent Claims
    claims = Claim.query.order_by(Claim.id.desc()).limit(10).all()

    return render_template(
        "admin/stock.html",
        inventory=inventory,
        history=history,
        claims=claims
    )


def _get_report_data(start_date_str, end_date_str, station_id, part_id):
    from app.models.consumption import Consumption
    from app.models.part import Part
    from app.models.station import Station
    from app.models.production_plan import ProductionPlan
    from app.models.scrap import Scrap
    from sqlalchemy import func

    # Base query
    query = (
        db.session.query(
            Consumption.recorded_at.label("timestamp"),
            Station.name.label("station_name"),
            Part.id.label("part_code"),
            Part.name.label("part_name"),
            Consumption.actual_qty.label("quantity_used"),
            func.sum(Scrap.scrap_qty).label("scrap_qty"),
            Part.current_stock.label("remaining_stock"),
            ProductionPlan.planned_qty,
        )
        .join(Station, Consumption.station_id == Station.id)
        .join(Part, Consumption.part_id == Part.id)
        .join(ProductionPlan, Consumption.order_id == ProductionPlan.order_id)
        .outerjoin(Scrap, Scrap.consumption_id == Consumption.id)
        .group_by(Consumption.id, Station.id, Part.id, ProductionPlan.order_id)
    )

    # Apply filters
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
            query = query.filter(Consumption.recorded_at >= start_date)
        except ValueError:
            pass
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59
            )
            query = query.filter(Consumption.recorded_at <= end_date)
        except ValueError:
            pass
    if station_id and station_id != "all":
        query = query.filter(Consumption.station_id == station_id)
    if part_id and part_id != "all":
        query = query.filter(Consumption.part_id == part_id)

    records = query.order_by(Consumption.recorded_at.desc()).all()
    return records


@bp.route("/reports")
@login_required
@role_required("admin")
def reports():
    from app.models.part import Part
    from app.models.station import Station

    # Get filter parameters
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")
    station_id = request.args.get("station_id")
    part_id = request.args.get("part_id")

    records = _get_report_data(start_date_str, end_date_str, station_id, part_id)

    # Process records for template
    report_data = []
    total_consumption = 0
    total_scrap = 0
    total_efficiency_sum = 0

    for r in records:
        used = int(r.quantity_used or 0)
        scrap = int(r.scrap_qty or 0)
        total_qty = used + scrap
        eff = round(float(used / total_qty * 100), 1) if total_qty > 0 else 0.0

        report_data.append(
            {
                "date": r.timestamp.strftime("%Y-%m-%d"),
                "station": r.station_name,
                "part_code": r.part_code,
                "part_name": r.part_name,
                "consumption": used,
                "scrap": scrap,
                "remaining_stock": int(r.remaining_stock or 0),
                "efficiency": eff,
            }
        )

        total_consumption += used
        total_scrap += scrap
        total_efficiency_sum += eff

    avg_efficiency = (total_efficiency_sum / len(records)) if records else 0

    # Get dropdown options
    all_stations = Station.query.all()
    all_parts = Part.query.all()

    return render_template(
        "admin/reports.html",
        report_data=report_data,
        total_records=len(records),
        total_consumption=total_consumption,
        total_scrap=total_scrap,
        avg_efficiency=round(avg_efficiency, 1),
        start_date=start_date_str,
        end_date=end_date_str,
        selected_station=station_id,
        selected_part=part_id,
        stations=all_stations,
        parts=all_parts,
    )


@bp.route("/reports/export")
@login_required
@role_required("admin")
def export_reports():
    import pandas as pd
    import io

    # Get filter parameters
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")
    station_id = request.args.get("station_id")
    part_id = request.args.get("part_id")

    records = _get_report_data(start_date_str, end_date_str, station_id, part_id)

    data = []
    for r in records:
        used = int(r.quantity_used or 0)
        scrap = int(r.scrap_qty or 0)
        total_qty = used + scrap
        eff = round(float(used / total_qty * 100), 1) if total_qty > 0 else 0.0
        data.append(
            {
                "Date": r.timestamp.strftime("%Y-%m-%d"),
                "Station": r.station_name,
                "Part Code": r.part_code,
                "Part Name": r.part_name,
                "Consumption": used,
                "Scrap": scrap,
                "Remaining Stock": int(r.remaining_stock or 0),
                "Efficiency %": f"{eff:.1f}%",
            }
        )

    df = pd.DataFrame(data)

    # Create Excel file in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Reports")

    output.seek(0)

    filename = (
        f"Factory_Report_{start_date_str or 'all'}_to_{end_date_str or 'all'}.xlsx"
    )

    return send_file(
        output,
        download_name=filename,
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
