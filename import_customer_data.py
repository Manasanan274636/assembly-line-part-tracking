import os
import pandas as pd
from datetime import datetime, date
from app import create_app
from app.utils.db import db
from app.models.user import User
from app.models.part import Part
from app.models.station import Station
from app.models.production_plan import ProductionPlan
from app.models.bom import BOM
from app.models.consumption import Consumption
from app.models.scrap import Scrap
from app.models.claim import Claim
from app.models.stock import Stock
from app.models.activity_log import ActivityLog


def import_customer_data():
    template_path = os.path.join(
        "เอกสารโปรเจค", "Assembly_Line_Tracking_Template_WITH_Mapping 2.xlsx"
    )
    att_path = os.path.join(
        "เอกสารโปรเจค", "att.izMXqlHji-tthFIWDQbxq2iU_-ZbOUi3Ja7FvI0upJU.xlsx"
    )
    claim_raw_path = os.path.join("เอกสารโปรเจค", "Claim Summary(1).xlsx")

    print("Reading Excel files...")
    xl = pd.ExcelFile(template_path)
    df_parts = xl.parse("parts")
    df_stations = xl.parse("stations")
    df_plans = xl.parse("production_plan")
    df_bom = xl.parse("bom")
    df_cons = xl.parse("consumption")
    df_claim = xl.parse("claim")

    df_att = pd.read_excel(att_path, sheet_name="All parts list")
    df_claim_parts = pd.read_excel(claim_raw_path, sheet_name="Part name")
    claim_part_name_map = {}
    for _, r in df_claim_parts.iterrows():
        pno = str(r.get("Part No.", "")).strip()
        pname = str(r.get("Part Name", "")).strip()
        if pno and pno != "nan":
            claim_part_name_map[pno] = pname

    app = create_app()
    with app.app_context():
        admin_user = User.query.filter_by(username="admin").first()
        admin_id = admin_user.user_id if admin_user else 1

        # 1. Import Parts (from parts sheet + any missing parts referenced by claim sheet)
        print("1. Importing parts...")
        existing_parts = {p.part_id: p for p in Part.query.all()}
        added_parts = 0

        for _, row in df_parts.iterrows():
            pid = str(row.get("part_id", "")).strip()
            if not pid or pid == "nan":
                continue
            pname = str(row.get("part_name", "")).strip() or pid
            raw_unit = row.get("unit")
            # In the mapping template, unit had numeric QTY/Veh (1, 2); normalize to 'pcs' if numeric
            if pd.isna(raw_unit) or str(raw_unit).strip().isdigit():
                unit = "pcs"
            else:
                unit = str(raw_unit).strip()[:20]

            stock_qty = int(row.get("stock_qty") or 0) if pd.notna(row.get("stock_qty")) else 0
            min_level = int(row.get("min_level") or 100) if pd.notna(row.get("min_level")) else 100
            max_level = int(row.get("max_level") or 300) if pd.notna(row.get("max_level")) else 300
            safety_stock = int(row.get("safety_stock") or 150) if pd.notna(row.get("safety_stock")) else 150
            is_active = int(row.get("is_active (1/0)") or 1) if pd.notna(row.get("is_active (1/0)")) else 1

            if pid not in existing_parts:
                p = Part(
                    part_id=pid[:50],
                    part_name=pname[:255],
                    unit=unit,
                    stock_qty=stock_qty,
                    min_level=min_level,
                    max_level=max_level,
                    safety_stock=safety_stock,
                    is_active=is_active,
                )
                db.session.add(p)
                existing_parts[pid[:50]] = p
                added_parts += 1

        # Ensure parts referenced in claim sheet also exist in parts table (FK constraint)
        for _, row in df_claim.iterrows():
            raw_pid = str(row.get("part_id", "")).strip()
            if not raw_pid or raw_pid == "nan":
                continue
            pid = " ".join(raw_pid.split())[:50]
            if pid not in existing_parts:
                first_code = pid.split(",")[0].strip()
                pname = claim_part_name_map.get(first_code, f"Part {pid}")
                p = Part(
                    part_id=pid,
                    part_name=pname[:255],
                    unit="pcs",
                    stock_qty=0,
                    min_level=100,
                    max_level=300,
                    safety_stock=150,
                    is_active=1,
                )
                db.session.add(p)
                existing_parts[pid] = p
                added_parts += 1

        db.session.commit()
        print(f"   -> Parts ready ({added_parts} added, total {len(existing_parts)}).")

        # 2. Import Stations (from stations sheet + All parts list stations)
        print("2. Importing stations...")
        station_map = {s.station_name: s for s in Station.query.all()}
        added_stations = 0

        station_names = []
        for _, row in df_att.iterrows():
            sname = str(row.get("Station", "")).strip()
            if sname and sname != "nan" and sname not in station_names:
                station_names.append(sname)
        for _, row in df_stations.iterrows():
            sname = str(row.get("station_name", "")).strip()
            if sname and sname != "nan" and sname not in station_names:
                station_names.append(sname)

        for sname in station_names:
            if sname not in station_map:
                st = Station(
                    station_name=sname[:100],
                    description=f"Assembly Station {sname}",
                    is_active=1,
                )
                db.session.add(st)
                db.session.flush()
                station_map[sname] = st
                added_stations += 1

        db.session.commit()
        print(f"   -> Stations ready ({added_stations} added, total {len(station_map)}).")

        # 3. Import Production Plan
        print("3. Importing production plans...")
        default_order_id = "MDEL_A_01"
        default_model_name = "Model A"
        for _, row in df_plans.iterrows():
            oid = str(row.get("order_id", "")).strip() or default_order_id
            mname = str(row.get("product_name", "")).strip() or default_model_name
            default_order_id = oid
            default_model_name = mname
            qty_plan = int(row.get("quantity_planned") or 1000)
            s_date = row.get("start_date")
            e_date = row.get("end_date")
            s_date = s_date.date() if hasattr(s_date, "date") else date(2026, 1, 1)
            e_date = e_date.date() if hasattr(e_date, "date") else date(2026, 12, 31)

            raw_status = str(row.get("status", "In Progress")).strip().lower()
            status = "In Progress" if raw_status == "in progress" else raw_status.title()

            if not ProductionPlan.query.filter_by(order_id=oid).first():
                plan = ProductionPlan(
                    order_id=oid,
                    product_name=mname,
                    quantity_planned=qty_plan,
                    start_date=s_date,
                    end_date=e_date,
                    status=status,
                    created_by=admin_id,
                )
                db.session.add(plan)

        db.session.commit()
        print(f"   -> Production plan '{default_order_id}' ({default_model_name}) ready.")

        # 4. Import BOM (linked to default_model_name = 'Model A')
        print("4. Importing BOM...")
        BOM.query.filter_by(model=default_model_name).delete()
        db.session.commit()

        bom_agg = {}
        for _, row in df_bom.iterrows():
            pid = str(row.get("part_id", "")).strip()
            if not pid or pid == "nan":
                continue
            qty_unit = int(row.get("qty_per_unit") or 1) if pd.notna(row.get("qty_per_unit")) else 1
            bom_agg[pid] = bom_agg.get(pid, 0) + qty_unit

        for pid, qty_unit in bom_agg.items():
            db.session.add(
                BOM(
                    bom_id=1,
                    model=default_model_name,
                    part_id=pid,
                    qty_per_unit=qty_unit,
                )
            )
        db.session.commit()
        print(f"   -> BOM ready ({len(bom_agg)} unique parts linked to '{default_model_name}').")

        # 5. Import Consumption (from consumption sheet + station/part mapping from All parts list)
        print("5. Importing consumption records...")
        existing_cons_count = Consumption.query.count()
        if existing_cons_count == 0:
            added_cons = 0
            for idx, row in df_cons.iterrows():
                att_row = df_att.iloc[idx] if idx < len(df_att) else None
                pid = str(row.get("part_id", "")).strip()
                if (not pid or pid == "nan") and att_row is not None:
                    pid = str(att_row.get("Part Number", "")).strip()

                sname = ""
                if att_row is not None:
                    sname = str(att_row.get("Station", "")).strip()
                st = station_map.get(sname) or list(station_map.values())[0]

                # In WITH_Mapping 2.xlsx, planned_qty was placed in consumption_id column
                planned_q = row.get("planned_qty")
                if pd.isna(planned_q):
                    planned_q = row.get("consumption_id")
                if pd.isna(planned_q) and att_row is not None:
                    planned_q = att_row.get("ยอดที่ต้องจ่ายออก", 0)
                planned_qty = int(planned_q or 0)

                actual_q = row.get("actual_qty")
                if pd.isna(actual_q) and att_row is not None:
                    actual_q = att_row.get("ยอดที่จ่ายได้จริง", 0)
                actual_qty = int(actual_q or 0)

                # In WITH_Mapping 2.xlsx, recorded_at date was placed in recorded_by column
                rec_date = row.get("recorded_at")
                if pd.isna(rec_date):
                    rec_date = row.get("recorded_by")
                if hasattr(rec_date, "to_pydatetime"):
                    rec_dt = rec_date.to_pydatetime()
                elif isinstance(rec_date, datetime):
                    rec_dt = rec_date
                else:
                    rec_dt = datetime(2026, 2, 25, 8, 0, 0)

                if pid and pid in existing_parts:
                    db.session.add(
                        Consumption(
                            order_id=default_order_id,
                            part_id=pid,
                            station_id=st.station_id,
                            planned_qty=planned_qty,
                            actual_qty=actual_qty,
                            recorded_by=admin_id,
                            recorded_at=rec_dt,
                        )
                    )
                    added_cons += 1
            db.session.commit()
            print(f"   -> Consumption records ready ({added_cons} rows added).")
        else:
            print(f"   -> Consumption already has {existing_cons_count} rows, skipping.")

        # 6. Import Claims
        print("6. Importing supplier claims...")
        added_claims = 0
        for _, row in df_claim.iterrows():
            cid = str(row.get("claim_id", "")).strip()
            if not cid or cid == "nan":
                continue
            raw_pid = str(row.get("part_id", "")).strip()
            pid = " ".join(raw_pid.split())[:50]
            qty = int(float(row.get("qty") or 0)) if pd.notna(row.get("qty")) else 0
            c_date = row.get("claim_date")
            c_date = c_date.date() if hasattr(c_date, "date") else date.today()
            c_status = str(row.get("claim_status", "Pending")).strip()[:100]

            if not Claim.query.filter_by(claim_id=cid).first():
                db.session.add(
                    Claim(
                        claim_id=cid[:50],
                        part_id=pid,
                        qty=qty,
                        claim_date=c_date,
                        claim_status=c_status,
                        recorded_by=admin_id,
                    )
                )
                added_claims += 1
        db.session.commit()
        print(f"   -> Supplier claims ready ({added_claims} added).")

        print("\nALL CUSTOMER DATA IMPORTED SUCCESSFULLY!")


if __name__ == "__main__":
    import_customer_data()
