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
from sqlalchemy import func, or_

bp = Blueprint("admin", __name__, url_prefix="/admin")


def _paginate_query(query, per_page=12, page_param="page"):
    page = request.args.get(page_param, 1, type=int)
    page = max(page, 1)
    total = query.count()
    items = query.limit(per_page).offset((page - 1) * per_page).all()
    total_pages = max((total + per_page - 1) // per_page, 1)
    return {
        "items": items,
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages,
        "has_prev": page > 1,
        "has_next": page < total_pages,
        "prev_num": page - 1,
        "next_num": page + 1,
        "page_param": page_param,
    }


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
    total_parts_units = db.session.query(func.sum(Part.stock_qty)).scalar() or 0
    # Number of SKUs low on stock (using min_level)
    low_stock_count = Part.query.filter(
        Part.stock_qty <= Part.min_level
    ).count()

    # Total scrap units (from scrap table)
    scrap_count = db.session.query(func.sum(Scrap.scrap_qty)).scalar() or 0

    # 2. Critical Alerts & Activity Feed
    alerts = []
    # Identify critical items
    critical_items = (
        Part.query.filter(Part.stock_qty < (Part.min_level / 2))
        .limit(3)
        .all()
    )
    
    for item in critical_items:
        alerts.append({
            "level": "CRITICAL",
            "title": "Stock Alert",
            "message": f"{item.part_name} ({item.part_id}): Critical stock ({item.stock_qty} {item.unit})",
            "time": "Recent"
        })

    # Get recent activity logs
    recent_activities = ActivityLog.query.order_by(ActivityLog.activity_id.desc()).limit(5).all()
    activity_feed = []
    for log in recent_activities:
        activity_feed.append({
            "type": log.activity_type,
            "message": log.message,
            "time": log.created_at.strftime("%H:%M")
        })

    # 3. Inventory & Usage Overview
    inventory_usage = []
    parts = Part.query.order_by(Part.stock_qty.asc()).limit(10).all()

    # --- OPTIMIZATION: Fix N+1 Query Problem ---
    # แทนที่จะ Query ทุกๆ รอบในลูป เราใช้การดึงค่ารวมทั้งหมดในครั้งเดียว (Batch Query)
    part_ids = [p.part_id for p in parts]
    
    if part_ids:
        # 3.1: Get actual_used for all Top 10 parts in ONE query
        used_query = (
            db.session.query(Consumption.part_id, func.sum(Consumption.actual_qty))
            .filter(Consumption.part_id.in_(part_ids))
            .group_by(Consumption.part_id)
            .all()
        )
        used_dict = {row.part_id: int(row[1]) for row in used_query if row[1]}

        # 3.2: Get scrap_qty in ONE query
        scrap_query = (
            db.session.query(Consumption.part_id, func.sum(Scrap.scrap_qty))
            .join(Scrap, Scrap.consumption_id == Consumption.consumption_id)
            .filter(Consumption.part_id.in_(part_ids))
            .group_by(Consumption.part_id)
            .all()
        )
        scrap_dict = {row.part_id: int(row[1]) for row in scrap_query if row[1]}

        # 3.3: Get required_qty from BOM in ONE query
        bom_query = (
            db.session.query(BOM.part_id, func.sum(BOM.qty_per_unit))
            .filter(BOM.part_id.in_(part_ids))
            .group_by(BOM.part_id)
            .all()
        )
        bom_dict = {row.part_id: int(row[1]) for row in bom_query if row[1]}
    else:
        used_dict, scrap_dict, bom_dict = {}, {}, {}

    for p in parts:
        actual_used = used_dict.get(p.part_id, 0)
        scrap_qty = scrap_dict.get(p.part_id, 0)
        required_qty = bom_dict.get(p.part_id, 0)

        status = "OK"
        if p.stock_qty == 0:
            status = "CRITICAL"
        elif p.stock_qty <= p.min_level:
            status = "Low Stock"

        inventory_usage.append({
            "name": p.part_name,
            "sku": p.part_id,
            "required_qty": required_qty,
            "actual_used": actual_used,
            "scrap": scrap_qty,
            "remaining_stock": p.stock_qty,
            "status": status,
        })

    # 4. Chart Data
    top_consumed = (
        db.session.query(Part.part_name, func.sum(Consumption.actual_qty).label("total"))
        .join(Consumption)
        .group_by(Part.part_id)
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


@bp.route("/users")
@login_required
@role_required("admin")
def users():
    from app.models.user import User
    q = (request.args.get("q") or "").strip()
    query = User.query.order_by(User.user_id.desc())
    if q:
        query = query.filter(
            or_(
                User.username.ilike(f"%{q}%"),
                User.email.ilike(f"%{q}%"),
                User.role.ilike(f"%{q}%"),
            )
        )
    users_page = _paginate_query(query, per_page=10)
    return render_template("admin/users.html", users=users_page["items"], pagination=users_page, q=q)


@bp.route("/users/add", methods=["POST"])
@login_required
@role_required("admin")
def add_user():
    from app.models.user import User
    from app.utils.db import db
    from app.models.activity_log import ActivityLog
    from flask_login import current_user
    
    username = request.form.get("username")
    email = request.form.get("email")
    role = request.form.get("role")
    password = request.form.get("password")
    
    if User.query.filter_by(username=username).first():
        flash("Username already exists.", "danger")
        return redirect(url_for("admin.users"))
        
    new_user = User(username=username, email=email, role=role)
    new_user.set_password(password)
    db.session.add(new_user)
    
    # Log activity
    log = ActivityLog(
        activity_type="User Management",
        reference_id="System",
        message=f"Admin created new user: {username} ({role})",
        created_by=current_user.user_id if hasattr(current_user, 'user_id') else current_user.id
    )
    db.session.add(log)
    
    db.session.commit()
    flash(f"User {username} added successfully!", "success")
    return redirect(url_for("admin.users"))


@bp.route("/users/toggle/<int:user_id>", methods=["POST"])
@login_required
@role_required("admin")
def toggle_user(user_id):
    from app.models.user import User
    from app.utils.db import db
    from app.models.activity_log import ActivityLog
    from flask_login import current_user
    
    user = User.query.get_or_404(user_id)
    current_uid = current_user.user_id if hasattr(current_user, 'user_id') else current_user.id
    if user.user_id == current_uid:
        flash("You cannot deactivate yourself.", "warning")
        return redirect(url_for("admin.users"))
        
    user.is_active_flag = 0 if user.is_active_flag == 1 else 1
    
    action = "Activated" if user.is_active_flag == 1 else "Deactivated"
    log = ActivityLog(
        activity_type="User Management",
        reference_id="System",
        message=f"Admin {action.lower()} user: {user.username}",
        created_by=current_uid
    )
    db.session.add(log)
    
    db.session.commit()
    flash(f"User {user.username} {action.lower()} successfully.", "success")
    return redirect(url_for("admin.users"))


@bp.route("/users/edit/<int:user_id>", methods=["POST"])
@login_required
@role_required("admin")
def edit_user(user_id):
    from app.models.user import User
    from app.utils.db import db
    from app.models.activity_log import ActivityLog
    from flask_login import current_user
    
    user = User.query.get_or_404(user_id)
    
    username = request.form.get("username")
    email = request.form.get("email")
    role = request.form.get("role")
    password = request.form.get("password")
    
    # Check if new username already exists for a DIFFERENT user
    existing_user = User.query.filter_by(username=username).first()
    if existing_user and existing_user.user_id != user_id:
        flash("Username already exists.", "danger")
        return redirect(url_for("admin.users"))
        
    user.username = username
    user.email = email
    user.role = role
    
    if password:  # If password is provided, update it
        user.set_password(password)
        
    log = ActivityLog(
        activity_type="User Management",
        reference_id="System",
        message=f"Admin updated user: {username}",
        created_by=current_user.user_id if hasattr(current_user, 'user_id') else current_user.id
    )
    db.session.add(log)
    
    db.session.commit()
    flash(f"User {username} updated successfully!", "success")
    return redirect(url_for("admin.users"))


# --- MASTER DATA: PARTS ---

@bp.route("/parts")
@login_required
@role_required("admin")
def parts():
    from app.models.part import Part
    q = (request.args.get("q") or "").strip()
    stock_sort = request.args.get("stock_sort", "name")
    query = Part.query
    if q:
        query = query.filter(
            or_(
                Part.part_id.ilike(f"%{q}%"),
                Part.part_name.ilike(f"%{q}%"),
                Part.unit.ilike(f"%{q}%"),
            )
        )

    if stock_sort == "stock_desc":
        query = query.order_by(Part.stock_qty.desc(), Part.part_name.asc())
    elif stock_sort == "stock_asc":
        query = query.order_by(Part.stock_qty.asc(), Part.part_name.asc())
    else:
        stock_sort = "name"
        query = query.order_by(Part.part_name.asc())

    parts_page = _paginate_query(query, per_page=10)
    return render_template(
        "admin/parts.html",
        parts=parts_page["items"],
        pagination=parts_page,
        q=q,
        stock_sort=stock_sort,
    )


@bp.route("/parts/add", methods=["POST"])
@login_required
@role_required("admin")
def add_part():
    from app.models.part import Part
    from app.utils.db import db
    from app.models.activity_log import ActivityLog
    from flask_login import current_user
    
    sku = request.form.get("sku")
    name = request.form.get("name")
    unit = request.form.get("unit", "pcs")
    min_stock = int(request.form.get("min_stock", 0))
    stock_qty = int(request.form.get("stock_qty", 0))
    
    if Part.query.filter_by(part_id=sku).first():
        flash(f"SKU {sku} already exists.", "danger")
        return redirect(url_for("admin.parts"))
        
    new_part = Part(
        part_id=sku,
        part_name=name,
        unit=unit,
        min_level=min_stock,
        stock_qty=stock_qty,
        is_active=1
    )
    db.session.add(new_part)
    
    log = ActivityLog(
        activity_type="Master Data",
        reference_id=sku,
        message=f"Admin added new part: {name} ({sku})",
        created_by=current_user.user_id if hasattr(current_user, 'user_id') else current_user.id
    )
    db.session.add(log)
    
    db.session.commit()
    flash(f"Part {name} added successfully!", "success")
    return redirect(url_for("admin.parts"))


@bp.route("/parts/edit/<part_id>", methods=["POST"])
@login_required
@role_required("admin")
def edit_part(part_id):
    from app.models.part import Part
    from app.utils.db import db
    from app.models.activity_log import ActivityLog
    from flask_login import current_user
    
    part = Part.query.get_or_404(part_id)
    
    part.part_name = request.form.get("name")
    part.unit = request.form.get("unit")
    part.min_level = int(request.form.get("min_stock", 0))
    
    # We do not allow changing SKU directly as it's the Primary Key in this schema.
    
    log = ActivityLog(
        activity_type="Master Data",
        reference_id=part.part_id,
        message=f"Admin updated part info: {part.part_name}",
        created_by=current_user.user_id if hasattr(current_user, 'user_id') else current_user.id
    )
    db.session.add(log)
    
    db.session.commit()
    flash(f"Part {part.part_name} updated successfully!", "success")
    return redirect(url_for("admin.parts"))


@bp.route("/parts/toggle/<part_id>", methods=["POST"])
@login_required
@role_required("admin")
def toggle_part(part_id):
    from app.models.part import Part
    from app.utils.db import db
    from app.models.activity_log import ActivityLog
    from flask_login import current_user
    
    part = Part.query.get_or_404(part_id)
    part.is_active = 0 if part.is_active == 1 else 1
    
    action = "Activated" if part.is_active == 1 else "Deactivated"
    log = ActivityLog(
        activity_type="Master Data",
        reference_id=part.part_id,
        message=f"Admin {action.lower()} part: {part.part_name}",
        created_by=current_user.user_id if hasattr(current_user, 'user_id') else current_user.id
    )
    db.session.add(log)
    
    db.session.commit()
    flash(f"Part {part.part_name} {action.lower()} successfully.", "success")
    return redirect(url_for("admin.parts"))


@bp.route("/parts/upload", methods=["POST"])
@login_required
@role_required("admin")
def upload_parts_master():
    if "excel_file" not in request.files:
        flash("No file picked", "danger")
        return redirect(url_for("admin.parts"))

    file = request.files["excel_file"]
    if file.filename == "":
        flash("No selected file", "danger")
        return redirect(url_for("admin.parts"))

    try:
        import pandas as pd
        from app.models.part import Part
        from app.utils.db import db
        from app.models.activity_log import ActivityLog
        from flask_login import current_user

        df = pd.read_excel(file)
        success_count = 0
        update_count = 0
        
        for _, row in df.iterrows():
            sku = str(row["SKU"]).strip()
            name = str(row.get("Part Name", ""))
            if not sku or not name or sku == "nan" or name == "nan":
                continue
                
            unit = str(row.get("Unit", "pcs")).strip()
            min_stock = int(row.get("Min Stock", 0))
            
            existing = Part.query.filter_by(part_id=sku).first()
            if existing:
                existing.part_name = name
                existing.unit = unit
                existing.min_level = min_stock
                update_count += 1
            else:
                initial_stock = int(row.get("Initial Stock", 0))
                new_part = Part(
                    part_id=sku,
                    part_name=name,
                    unit=unit,
                    min_level=min_stock,
                    stock_qty=initial_stock,
                    is_active=1
                )
                db.session.add(new_part)
                success_count += 1

        log = ActivityLog(
            activity_type="Master Data Import",
            reference_id="Batch_Part",
            message=f"Admin uploaded Part Master data ({success_count} added, {update_count} updated)",
            created_by=current_user.user_id if hasattr(current_user, 'user_id') else current_user.id
        )
        db.session.add(log)
        db.session.commit()
        
        flash(f"Successfully added {success_count} new parts and updated {update_count} existing parts.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error processing Excel: {str(e)}", "danger")

    return redirect(url_for("admin.parts"))


@bp.route("/parts/template")
@login_required
@role_required("admin")
def download_parts_template():
    output = io.BytesIO()
    df = pd.DataFrame(
        [
            {
                "SKU": "P-1001",
                "Part Name": "Bracket Assembly",
                "Unit": "pcs",
                "Min Stock": 50,
                "Initial Stock": 200,
            },
            {
                "SKU": "P-1002",
                "Part Name": "Bolt M8",
                "Unit": "pcs",
                "Min Stock": 100,
                "Initial Stock": 1000,
            },
        ]
    )

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Part Master Template")

    output.seek(0)
    return send_file(
        output,
        download_name="part_master_template.xlsx",
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# --- MASTER DATA: STATIONS ---

@bp.route("/stations")
@login_required
@role_required("admin")
def stations():
    from app.models.station import Station
    q = (request.args.get("q") or "").strip()
    query = Station.query.order_by(Station.station_id.asc())
    if q:
        query = query.filter(
            or_(
                Station.station_name.ilike(f"%{q}%"),
                Station.description.ilike(f"%{q}%"),
            )
        )
    stations_page = _paginate_query(query, per_page=10)
    return render_template("admin/stations.html", stations=stations_page["items"], pagination=stations_page, q=q)


@bp.route("/stations/add", methods=["POST"])
@login_required
@role_required("admin")
def add_station():
    from app.models.station import Station
    from app.utils.db import db
    from app.models.activity_log import ActivityLog
    from flask_login import current_user
    
    name = request.form.get("name")
    description = request.form.get("description", "")
    
    existing = Station.query.filter_by(station_name=name).first()
    if existing:
        flash(f"Station name '{name}' already exists.", "danger")
        return redirect(url_for("admin.stations"))
        
    new_station = Station(
        station_name=name,
        description=description,
        is_active=1
    )
    db.session.add(new_station)
    
    log = ActivityLog(
        activity_type="Master Data",
        reference_id="Station",
        message=f"Admin added new station: {name}",
        created_by=current_user.user_id if hasattr(current_user, 'user_id') else current_user.id
    )
    db.session.add(log)
    
    db.session.commit()
    flash(f"Station {name} added successfully!", "success")
    return redirect(url_for("admin.stations"))


@bp.route("/stations/edit/<int:station_id>", methods=["POST"])
@login_required
@role_required("admin")
def edit_station(station_id):
    from app.models.station import Station
    from app.utils.db import db
    from app.models.activity_log import ActivityLog
    from flask_login import current_user
    
    station = Station.query.get_or_404(station_id)
    
    name = request.form.get("name")
    existing_name = Station.query.filter_by(station_name=name).first()
    if existing_name and existing_name.station_id != station_id:
        flash(f"Station name '{name}' already exists.", "danger")
        return redirect(url_for("admin.stations"))
    
    station.station_name = name
    station.description = request.form.get("description", "")
    
    log = ActivityLog(
        activity_type="Master Data",
        reference_id=f"Station_{station.station_id}",
        message=f"Admin updated station info: {station.station_name}",
        created_by=current_user.user_id if hasattr(current_user, 'user_id') else current_user.id
    )
    db.session.add(log)
    
    db.session.commit()
    flash(f"Station {station.station_name} updated successfully!", "success")
    return redirect(url_for("admin.stations"))


@bp.route("/stations/toggle/<int:station_id>", methods=["POST"])
@login_required
@role_required("admin")
def toggle_station(station_id):
    from app.models.station import Station
    from app.utils.db import db
    from app.models.activity_log import ActivityLog
    from flask_login import current_user
    
    station = Station.query.get_or_404(station_id)
    station.is_active = 0 if station.is_active == 1 else 1
    
    action = "Activated" if station.is_active == 1 else "Deactivated"
    log = ActivityLog(
        activity_type="Master Data",
        reference_id=f"Station_{station.station_id}",
        message=f"Admin {action.lower()} station: {station.station_name}",
        created_by=current_user.user_id if hasattr(current_user, 'user_id') else current_user.id
    )
    db.session.add(log)
    
    db.session.commit()
    flash(f"Station {station.station_name} {action.lower()} successfully.", "success")
    return redirect(url_for("admin.stations"))


# --- MASTER DATA: BOM (BILL OF MATERIALS) ---

@bp.route("/bom")
@login_required
@role_required("admin")
def bom():
    from app.models.bom import BOM
    from app.models.part import Part
    from app.models.activity_log import ActivityLog
    q = (request.args.get("q") or "").strip()

    # Query all parts for the select dropdown
    parts = Part.query.filter_by(is_active=1).order_by(Part.part_name).all()

    bom_query = BOM.query
    if q:
        bom_query = bom_query.filter(BOM.model.ilike(f"%{q}%"))

    # Get all BOM entries
    bom_entries = bom_query.order_by(BOM.model, BOM.part_id).all()
    
    # Group BOM entries by model for display
    bom_grouped = {}
    for b in bom_entries:
        if b.model not in bom_grouped:
            bom_grouped[b.model] = []
        bom_grouped[b.model].append(b)

    ref_ids = [f"BOM_{model_name}" for model_name in bom_grouped.keys()]
    log_summary = {}
    if ref_ids:
        log_rows = (
            db.session.query(
                ActivityLog.reference_id,
                func.min(ActivityLog.created_at).label("created_at"),
                func.max(ActivityLog.created_at).label("updated_at"),
            )
            .filter(ActivityLog.reference_id.in_(ref_ids))
            .group_by(ActivityLog.reference_id)
            .all()
        )
        log_summary = {
            row.reference_id: {"created_at": row.created_at, "updated_at": row.updated_at}
            for row in log_rows
        }

    bom_meta = {}
    for model_name, entries in bom_grouped.items():
        ref_id = f"BOM_{model_name}"
        log_info = log_summary.get(ref_id, {})
        bom_meta[model_name] = {
            "parts_count": len(entries),
            "created_at": log_info.get("created_at"),
            "updated_at": log_info.get("updated_at"),
        }
        
    return render_template(
        "admin/bom.html",
        bom_grouped=bom_grouped,
        bom_meta=bom_meta,
        parts=parts,
        q=q,
    )


@bp.route("/bom/add", methods=["POST"])
@login_required
@role_required("admin")
def add_bom_entry():
    from app.models.bom import BOM
    from app.utils.db import db
    from app.models.activity_log import ActivityLog
    from flask_login import current_user
    
    model_name = (request.form.get("model") or "").strip()
    part_ids = request.form.getlist("part_id")
    qty_values = request.form.getlist("qty_per_unit")

    if not model_name:
        flash("Product model is required.", "danger")
        return redirect(url_for("admin.bom"))

    rows = []
    for index, raw_part_id in enumerate(part_ids):
        part_id = (raw_part_id or "").strip()
        raw_qty = qty_values[index] if index < len(qty_values) else "0"

        if not part_id:
            continue

        try:
            qty = int(raw_qty)
        except (TypeError, ValueError):
            flash(f"Invalid quantity for part {part_id}.", "danger")
            return redirect(url_for("admin.bom"))

        if qty <= 0:
            flash(f"Quantity for part {part_id} must be greater than zero.", "danger")
            return redirect(url_for("admin.bom"))

        rows.append((part_id, qty))

    if not rows:
        flash("Please add at least one BOM item.", "danger")
        return redirect(url_for("admin.bom"))

    unique_part_ids = set()
    for part_id, _qty in rows:
        if part_id in unique_part_ids:
            flash(f"Part {part_id} is duplicated in the form.", "warning")
            return redirect(url_for("admin.bom"))
        unique_part_ids.add(part_id)

    existing_model_bom = BOM.query.filter_by(model=model_name).first()
    if existing_model_bom:
        bom_id = existing_model_bom.bom_id
    else:
        max_id_bom = BOM.query.order_by(BOM.bom_id.desc()).first()
        bom_id = (max_id_bom.bom_id + 1) if max_id_bom else 1

    added_count = 0
    skipped_parts = []

    for part_id, qty in rows:
        existing_entry = BOM.query.filter_by(model=model_name, part_id=part_id).first()
        if existing_entry:
            skipped_parts.append(part_id)
            continue

        db.session.add(
            BOM(bom_id=bom_id, model=model_name, part_id=part_id, qty_per_unit=qty)
        )
        added_count += 1

    if added_count == 0:
        flash(
            f"No new BOM items were added. Existing parts in {model_name}: {', '.join(skipped_parts)}",
            "warning",
        )
        return redirect(url_for("admin.bom"))

    log_message = f"Admin added {added_count} part(s) to BOM {model_name}"
    if skipped_parts:
        log_message += f" (skipped existing: {', '.join(skipped_parts)})"

    db.session.add(
        ActivityLog(
            activity_type="Master Data",
            reference_id=f"BOM_{model_name}",
            message=log_message,
            created_by=current_user.user_id
        )
    )
    db.session.commit()

    if skipped_parts:
        flash(
            f"Added {added_count} BOM item(s). Skipped existing part(s): {', '.join(skipped_parts)}",
            "warning",
        )
    else:
        flash(f"Successfully added {added_count} BOM item(s) to {model_name}.", "success")
    return redirect(url_for("admin.bom"))


@bp.route("/bom/edit/<model_name>/<part_id>", methods=["POST"])
@login_required
@role_required("admin")
def edit_bom_entry(model_name, part_id):
    from app.models.bom import BOM
    from app.models.activity_log import ActivityLog
    from flask_login import current_user

    entry = BOM.query.filter_by(model=model_name, part_id=part_id).first_or_404()
    qty = int(request.form.get("qty_per_unit", 1))

    if qty <= 0:
        flash("Quantity per unit must be greater than zero.", "danger")
        return redirect(url_for("admin.bom"))

    entry.qty_per_unit = qty
    db.session.add(
        ActivityLog(
            activity_type="Master Data",
            reference_id=f"BOM_{model_name}",
            message=f"Admin updated BOM quantity for {part_id} in {model_name} to {qty}",
            created_by=current_user.user_id,
        )
    )
    db.session.commit()

    flash(f"Updated {part_id} quantity in {model_name} BOM.", "success")
    return redirect(url_for("admin.bom"))


@bp.route("/bom/model/<model_name>/edit", methods=["POST"])
@login_required
@role_required("admin")
def edit_bom_model(model_name):
    from app.models.bom import BOM
    from app.models.activity_log import ActivityLog
    from flask_login import current_user

    part_ids = request.form.getlist("part_id")
    qty_values = request.form.getlist("qty_per_unit")

    rows = []
    for index, raw_part_id in enumerate(part_ids):
        part_id = (raw_part_id or "").strip()
        raw_qty = qty_values[index] if index < len(qty_values) else "0"

        if not part_id:
            continue

        try:
            qty = int(raw_qty)
        except (TypeError, ValueError):
            flash(f"Invalid quantity for part {part_id}.", "danger")
            return redirect(url_for("admin.bom"))

        if qty <= 0:
            flash(f"Quantity for part {part_id} must be greater than zero.", "danger")
            return redirect(url_for("admin.bom"))

        rows.append((part_id, qty))

    if not rows:
        flash("A BOM model must contain at least one part.", "danger")
        return redirect(url_for("admin.bom"))

    unique_part_ids = set()
    for part_id, _qty in rows:
        if part_id in unique_part_ids:
            flash(f"Part {part_id} is duplicated in the form.", "warning")
            return redirect(url_for("admin.bom"))
        unique_part_ids.add(part_id)

    existing_entries = BOM.query.filter_by(model=model_name).all()
    if not existing_entries:
        flash(f"BOM model {model_name} was not found.", "danger")
        return redirect(url_for("admin.bom"))

    bom_id = existing_entries[0].bom_id
    existing_map = {entry.part_id: entry for entry in existing_entries}
    incoming_map = {part_id: qty for part_id, qty in rows}

    updated_count = 0
    added_count = 0
    removed_count = 0

    for part_id, entry in existing_map.items():
        if part_id not in incoming_map:
            db.session.delete(entry)
            removed_count += 1
            continue

        new_qty = incoming_map[part_id]
        if entry.qty_per_unit != new_qty:
            entry.qty_per_unit = new_qty
            updated_count += 1

    for part_id, qty in incoming_map.items():
        if part_id in existing_map:
            continue
        db.session.add(BOM(bom_id=bom_id, model=model_name, part_id=part_id, qty_per_unit=qty))
        added_count += 1

    db.session.add(
        ActivityLog(
            activity_type="Master Data",
            reference_id=f"BOM_{model_name}",
            message=(
                f"Admin edited BOM {model_name} "
                f"(added: {added_count}, updated: {updated_count}, removed: {removed_count})"
            ),
            created_by=current_user.user_id,
        )
    )
    db.session.commit()

    flash(
        f"BOM {model_name} updated successfully. Added {added_count}, updated {updated_count}, removed {removed_count}.",
        "success",
    )
    return redirect(url_for("admin.bom"))


@bp.route("/bom/delete/<model_name>/<part_id>", methods=["POST"])
@login_required
@role_required("admin")
def delete_bom_entry(model_name, part_id):
    from app.models.bom import BOM
    from app.utils.db import db
    from app.models.activity_log import ActivityLog
    from flask_login import current_user
    
    entry = BOM.query.filter_by(model=model_name, part_id=part_id).first_or_404()
    
    db.session.delete(entry)
    
    log = ActivityLog(
        activity_type="Master Data",
        reference_id=f"BOM_{model_name}",
        message=f"Admin removed part {part_id} from BOM {model_name}",
        created_by=current_user.user_id if hasattr(current_user, 'user_id') else current_user.id
    )
    db.session.add(log)
    db.session.commit()
    
    flash(f"Removed {part_id} from {model_name} BOM.", "success")
    return redirect(url_for("admin.bom"))


# --- PRODUCTION PLAN CREATION ---

@bp.route("/production/add", methods=["POST"])
@login_required
@role_required("admin")
def add_production():
    from app.models.production_plan import ProductionPlan
    from app.utils.db import db
    from app.models.activity_log import ActivityLog
    from flask_login import current_user
    import datetime
    
    order_id = request.form.get("order_id")
    product_name = request.form.get("product_name")
    qty = int(request.form.get("quantity", 0))
    start_date_str = request.form.get("start_date")
    end_date_str = request.form.get("end_date") or start_date_str
    
    if ProductionPlan.query.filter_by(order_id=order_id).first():
        flash(f"Order ID {order_id} already exists.", "danger")
        # Ensure 'admin.production' route exists. Fallback if it is named differently:
        try:
            return redirect(url_for("admin.production"))
        except Exception:
            return redirect(url_for("admin.dashboard"))
        
    start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
    end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()

    if end_date < start_date:
        flash("End date must be the same as or later than start date.", "danger")
        return redirect(url_for("admin.production"))

    plan = ProductionPlan(
        order_id=order_id,
        product_name=product_name,
        quantity_planned=qty,
        start_date=start_date,
        end_date=end_date,
        status="In Progress",
        created_by=current_user.user_id if hasattr(current_user, 'user_id') else current_user.id
    )
    db.session.add(plan)
    
    log = ActivityLog(
        activity_type="Production",
        reference_id=order_id,
        message=f"Admin created production plan for {product_name} (Qty: {qty})",
        created_by=current_user.user_id if hasattr(current_user, 'user_id') else current_user.id
    )
    db.session.add(log)
    db.session.commit()
    
    flash("Production plan created successfully.", "success")
    try:
        return redirect(url_for("admin.production"))
    except Exception:
        return redirect(url_for("admin.dashboard"))


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
        planned_qty=quantity_used,
        recorded_by=current_user.user_id
    )

    # Update part stock
    part = Part.query.get(part_id)
    if part:
        part.stock_qty -= (quantity_used + scrap_qty)
        
    db.session.add(new_consumption)
    db.session.flush() # Get consumption ID for scrap

    if scrap_qty > 0:
        from app.models.scrap import Scrap
        new_scrap = Scrap(
            consumption_id=new_consumption.consumption_id,
            scrap_qty=scrap_qty,
            reason="Manual Entry"
        )
        db.session.add(new_scrap)

    # Log activity
    log = ActivityLog(
        activity_type="Data Entry",
        reference_id=plan.order_id,
        message=f"Admin recorded {quantity_used} units for {part.part_id}",
        created_by=current_user.user_id
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
                station_name=str(row["StationName"]).strip()
            ).first()
            part = Part.query.filter_by(part_id=str(row["PartSKU"]).strip()).first()

            if station and part:
                # Find active plan
                plan = ProductionPlan.query.filter_by(status="In Progress").first()
                if not plan:
                    plan = ProductionPlan.query.order_by(ProductionPlan.order_id.desc()).first()

                if plan:
                    qty = int(row["QuantityUsed"])
                    scrap_qty = int(row.get("ScrapQty", 0))

                    cons = Consumption(
                        station_id=station.station_id,
                        part_id=part.part_id,
                        order_id=plan.order_id,
                        planned_qty=qty,
                        actual_qty=qty,
                        recorded_by=current_user.user_id
                    )
                    db.session.add(cons)
                    db.session.flush()

                    if scrap_qty > 0:
                        new_scrap = Scrap(
                            consumption_id=cons.consumption_id,
                            scrap_qty=scrap_qty,
                            reason="Excel Upload"
                        )
                        db.session.add(new_scrap)
                    
                    part.stock_qty -= (qty + scrap_qty)
                    success_count += 1

        if success_count > 0:
            log = ActivityLog(
                activity_type="Excel Import",
                message=f"Imported {success_count} records via Excel",
                created_by=current_user.user_id
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

    selected_order_id = request.args.get("order_id")
    plans = ProductionPlan.query.order_by(
        ProductionPlan.start_date.desc(), ProductionPlan.order_id.desc()
    ).all()

    plan = None
    if selected_order_id:
        plan = ProductionPlan.query.get(selected_order_id)
    if not plan:
        plan = ProductionPlan.query.filter_by(status="In Progress").order_by(
            ProductionPlan.start_date.desc()
        ).first()
    if not plan and plans:
        plan = plans[0]

    bom_items = []
    total_part_types = 0
    total_items_required = 0
    total_items_used = 0

    if plan:
        # Get BOM for this plan's product model
        boms = BOM.query.filter_by(model=plan.product_name).all()
        total_part_types = len(boms)

        for b in boms:
            part = b.part
            qty_per_unit = b.qty_per_unit
            calculated_required = qty_per_unit * plan.quantity_planned
            total_items_required += calculated_required

            # Get actual consumption for this part in this plan
            actual_used = db.session.query(func.sum(Consumption.actual_qty)).filter_by(
                order_id=plan.order_id, part_id=b.part_id
            ).scalar() or 0
            total_items_used += int(actual_used)

            bom_items.append({
                "part_code": part.part_id,
                "part_name": part.part_name,
                "qty_per_unit": round(qty_per_unit, 2),
                "unit": part.unit or "pcs",
                "calculated_required": calculated_required,
                "actual_used": actual_used,
                "remaining_required": max(calculated_required - actual_used, 0),
                "percentage": round((actual_used / calculated_required * 100), 1) if calculated_required > 0 else 0
            })

    shift_info = (
        f"{plan.start_date} to {plan.end_date}"
        if plan and plan.start_date and plan.end_date and plan.start_date != plan.end_date
        else (str(plan.start_date) if plan and plan.start_date else "No active period")
    )
    product_name = plan.product_name if plan else "N/A"

    return render_template(
        "admin/production.html",
        plans=plans,
        plan=plan,
        bom_items=bom_items,
        total_part_types=total_part_types,
        total_items_required=total_items_required,
        total_items_used=total_items_used,
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

    q = (request.args.get("q") or "").strip()
    inventory_query = Part.query.order_by(Part.stock_qty.asc(), Part.part_name.asc())
    if q:
        inventory_query = inventory_query.filter(
            or_(
                Part.part_id.ilike(f"%{q}%"),
                Part.part_name.ilike(f"%{q}%"),
                Part.unit.ilike(f"%{q}%"),
            )
        )

    inventory_page = _paginate_query(inventory_query, per_page=10, page_param="inv_page")
    history_page = _paginate_query(
        Stock.query.order_by(Stock.stock_id.desc()), per_page=10, page_param="hist_page"
    )
    claims_page = _paginate_query(
        Claim.query.order_by(Claim.claim_id.desc()), per_page=10, page_param="claim_page"
    )

    return render_template(
        "admin/stock.html",
        inventory=inventory_page["items"],
        history=history_page["items"],
        claims=claims_page["items"],
        inventory_pagination=inventory_page,
        history_pagination=history_page,
        claims_pagination=claims_page,
        q=q,
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
            Station.station_name.label("station_name"),
            Part.part_id.label("part_code"),
            Part.part_name.label("part_name"),
            Consumption.actual_qty.label("quantity_used"),
            func.sum(Scrap.scrap_qty).label("scrap_qty"),
            Part.stock_qty.label("remaining_stock"),
            ProductionPlan.quantity_planned,
        )
        .join(Station, Consumption.station_id == Station.station_id)
        .join(Part, Consumption.part_id == Part.part_id)
        .join(ProductionPlan, Consumption.order_id == ProductionPlan.order_id)
        .outerjoin(Scrap, Scrap.consumption_id == Consumption.consumption_id)
        .group_by(Consumption.consumption_id, Station.station_id, Part.part_id, ProductionPlan.order_id)
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

    return query.order_by(Consumption.recorded_at.desc())


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

    records_query = _get_report_data(start_date_str, end_date_str, station_id, part_id)
    reports_page = _paginate_query(records_query, per_page=20, page_param="page")
    records = reports_page["items"]

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
        pagination=reports_page,
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

    records = _get_report_data(start_date_str, end_date_str, station_id, part_id).all()

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
