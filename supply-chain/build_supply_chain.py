"""
Riverbend Health System - supply chain data generator.

A made-up hospital supply chain for a year (2025): the item master, vendors,
group-purchasing contracts, purchase orders, receipts, invoices, surgical cases
and the supplies they used, surgeon preference cards, daily inventory counts,
and backorders.

Like the rest of Riverbend, the mess is deliberate. Duplicate items and
vendors, contract prices that changed mid-year, invoices that don't match
their orders, units of measure that don't line up, a surgeon who never
switched implants. Don't fix this file; find the problems with SQL.

Surgeon IDs are Riverbend provider IDs (PRV0002, PRV0006, ...), so these
tables can be joined to raw_providers in data/riverbend.db later.

Standard library only. Same seed, same data, every time.

Usage:
    python build_supply_chain.py
"""

import csv
import math
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

SEED = 20251015
HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
DB = HERE / "supply_chain.db"

YEAR_START = date(2025, 1, 1)
AS_OF = date(2025, 12, 15)              # "today" in this dataset
SWITCH = date(2025, 7, 1)               # new contract year starts; knee/hip conversion
GLOVE_PO_FIX = date(2025, 11, 1)        # PO system finally loads the new glove price
BACKORDER_START = date(2025, 8, 4)      # glove and gauze backorder at the main distributor
BACKORDER_END = date(2025, 9, 15)
PM_OVERBILL_END = date(2025, 9, 30)     # pacemaker vendor keeps billing the old price until here
HOLIDAYS = {date(2025, 1, 1), date(2025, 1, 20), date(2025, 5, 26), date(2025, 7, 4),
            date(2025, 9, 1), date(2025, 11, 27), date(2025, 11, 28), date(2025, 12, 25)}

LOCATIONS = [
    ("L01", "Main OR", "Perioperative"),
    ("L02", "Cath/EP Lab", "Cardiology"),
    ("L03", "Central Supply", "Supply Chain"),
    ("L04", "5 North Med-Surg", "Nursing"),
]

# vendor_id, name, type, tax_id. V008 and V009 are duplicate records of V003 and V001.
VENDORS = [
    ("V001", "Northbridge Medical Distribution", "Distributor", "54-3318820"),
    ("V002", "Keystone Surgical Supply", "Distributor", "23-7741902"),
    ("V003", "Apex Orthopedics, Inc.", "Manufacturer", "41-2290573"),
    ("V004", "Meridian Joint Systems", "Manufacturer", "36-8804117"),
    ("V005", "Cardiolinx Medical", "Manufacturer", "27-5521346"),
    ("V006", "Pulsar EP Systems", "Manufacturer", "84-1067752"),
    ("V007", "Bluegate Med-Surg", "Distributor", "62-4409381"),
    ("V008", "APEX ORTHOPEDICS INC", "Manufacturer", "41-2290573"),
    ("V009", "Northbridge Medical Dist.", "Distributor", "54-3318820"),
]
INVOICE_PREFIX = {"V001": "NMD", "V002": "KSS", "V003": "APX", "V004": "MJS", "V005": "CLX",
                  "V006": "PEP", "V007": "BGM", "V008": "APX", "V009": "NMD"}

# key, description, manufacturer, catalog no, vendor, category, uom, units/uom,
# list price, contract price Jan-Jun, contract price Jul-Dec (None = no contract), implant
ITEMS = [
    ("APX_FEM", "Apex CR Femoral Component", "Apex Orthopedics", "APX-FC-4410", "V003", "Ortho Implant", "EA", 1, 3400.00, 2900.00, None, 1),
    ("APX_TIB", "Apex Tibial Baseplate", "Apex Orthopedics", "APX-TB-2210", "V003", "Ortho Implant", "EA", 1, 2500.00, 2100.00, None, 1),
    ("APX_INS", "Apex Tibial Insert, Poly", "Apex Orthopedics", "APX-TI-1120", "V003", "Ortho Implant", "EA", 1, 1450.00, 1200.00, None, 1),
    ("APX_PAT", "Apex Patella Button", "Apex Orthopedics", "APX-PB-0510", "V003", "Ortho Implant", "EA", 1, 720.00, 600.00, None, 1),
    ("APX_STEM", "Apex Hip Stem, Cementless", "Apex Orthopedics", "APX-HS-3300", "V003", "Ortho Implant", "EA", 1, 3600.00, 3100.00, None, 1),
    ("APX_SHELL", "Apex Acetabular Shell", "Apex Orthopedics", "APX-AS-2400", "V003", "Ortho Implant", "EA", 1, 2300.00, 1950.00, None, 1),
    ("APX_HEAD", "Apex Ceramic Femoral Head", "Apex Orthopedics", "APX-FH-1300", "V003", "Ortho Implant", "EA", 1, 1500.00, 1250.00, None, 1),
    ("APX_LINER", "Apex Acetabular Liner", "Apex Orthopedics", "APX-AL-0900", "V003", "Ortho Implant", "EA", 1, 1100.00, 900.00, None, 1),
    ("MJS_FEM", "Meridian Femoral Component, CR", "Meridian Joint Systems", "MJS-F-100", "V004", "Ortho Implant", "EA", 1, 2300.00, 1800.00, 1750.00, 1),
    ("MJS_TIB", "Meridian Tibial Tray", "Meridian Joint Systems", "MJS-T-200", "V004", "Ortho Implant", "EA", 1, 1700.00, 1350.00, 1300.00, 1),
    ("MJS_INS", "Meridian Tibial Insert", "Meridian Joint Systems", "MJS-I-300", "V004", "Ortho Implant", "EA", 1, 950.00, 750.00, 720.00, 1),
    ("MJS_PAT", "Meridian Patella", "Meridian Joint Systems", "MJS-P-400", "V004", "Ortho Implant", "EA", 1, 520.00, 400.00, 390.00, 1),
    ("MJS_STEM", "Meridian Hip Stem", "Meridian Joint Systems", "MJS-S-500", "V004", "Ortho Implant", "EA", 1, 2600.00, 2050.00, 1990.00, 1),
    ("MJS_SHELL", "Meridian Acetabular Cup", "Meridian Joint Systems", "MJS-C-600", "V004", "Ortho Implant", "EA", 1, 1650.00, 1300.00, 1260.00, 1),
    ("MJS_HEAD", "Meridian Femoral Head", "Meridian Joint Systems", "MJS-H-700", "V004", "Ortho Implant", "EA", 1, 1100.00, 850.00, 830.00, 1),
    ("MJS_LINER", "Meridian Poly Liner", "Meridian Joint Systems", "MJS-L-800", "V004", "Ortho Implant", "EA", 1, 760.00, 600.00, 580.00, 1),
    ("PM", "Dual-Chamber Pacemaker", "Cardiolinx Medical", "CLX-PM-DR", "V005", "Cardiac Implant", "EA", 1, 6100.00, 5200.00, 4940.00, 1),
    ("PM_LEAD", "Pacing Lead, 58 cm", "Cardiolinx Medical", "CLX-LD-58", "V005", "Cardiac Implant", "EA", 1, 1000.00, 850.00, 850.00, 1),
    ("ICD", "ICD, Single Chamber", "Cardiolinx Medical", "CLX-ICD-VR", "V005", "Cardiac Implant", "EA", 1, 21000.00, 18500.00, 18500.00, 1),
    ("ICD_LEAD", "Defibrillation Lead", "Cardiolinx Medical", "CLX-DL-65", "V005", "Cardiac Implant", "EA", 1, 2800.00, 2400.00, 2400.00, 1),
    ("INTRO", "Peel-Away Introducer, 7 Fr", "Cardiolinx Medical", "CLX-IN-07", "V005", "Cardiac Supply", "BX", 10, 1400.00, 1200.00, 1200.00, 0),
    ("ABL", "Ablation Catheter, Contact Force", "Pulsar EP Systems", "PEP-AC-CF", "V006", "EP Catheter", "EA", 1, 4500.00, 3900.00, 3900.00, 0),
    ("MAP", "Mapping Catheter, Multipolar", "Pulsar EP Systems", "PEP-MC-20", "V006", "EP Catheter", "EA", 1, 2500.00, 2100.00, 2100.00, 0),
    ("SHEATH", "Transseptal Sheath", "Pulsar EP Systems", "PEP-TS-85", "V006", "EP Catheter", "EA", 1, 560.00, 480.00, 480.00, 0),
    ("CEMENT", "Bone Cement, 40 g", "Keystone Surgical", "KSS-BC-40", "V002", "Surgical Supply", "EA", 1, 210.00, 180.00, 180.00, 0),
    ("MIXER", "Cement Mixing System", "Keystone Surgical", "KSS-MX-01", "V002", "Surgical Supply", "EA", 1, 110.00, 95.00, 95.00, 0),
    ("DRAPE", "Surgical Drape Pack, Ortho", "Keystone Surgical", "KSS-DP-OR", "V002", "Surgical Supply", "EA", 1, 80.00, 65.00, 65.00, 0),
    ("DRAPE_CV", "Surgical Drape Pack, Cardiac", "Keystone Surgical", "KSS-DP-CV", "V002", "Surgical Supply", "EA", 1, 75.00, 60.00, 60.00, 0),
    ("GOWN", "Surgical Gown, Large", "Keystone Surgical", "KSS-GW-L", "V002", "Surgical Supply", "BX", 20, 175.00, 140.00, 140.00, 0),
    ("BLADE", "Sagittal Saw Blade", "Keystone Surgical", "KSS-SB-90", "V002", "Surgical Supply", "EA", 1, 110.00, 95.00, 95.00, 0),
    ("SUTURE", "Suture Pack, 2-0", "Keystone Surgical", "KSS-SU-20", "V002", "Surgical Supply", "BX", 36, 360.00, 310.00, 310.00, 0),
    ("STAPLER", "Skin Stapler, 35W", "Keystone Surgical", "KSS-ST-35", "V002", "Surgical Supply", "EA", 1, 55.00, 45.00, 45.00, 0),
    ("GLOVE", "Exam Gloves, Nitrile, Medium", "Northbridge", "NMD-GL-M", "V001", "Med-Surg Commodity", "BX", 100, 12.00, 9.50, 10.25, 0),
    ("SYRINGE", "Syringe, 10 mL Luer Lock", "Northbridge", "NMD-SY-10", "V001", "Med-Surg Commodity", "BX", 100, 18.00, 14.00, 14.00, 0),
    ("IVKIT", "IV Start Kit", "Northbridge", "NMD-IV-01", "V001", "Med-Surg Commodity", "BX", 50, 105.00, 85.00, 85.00, 0),
    ("GAUZE", "Gauze Sponge, 4x4", "Northbridge", "NMD-GZ-44", "V001", "Med-Surg Commodity", "BX", 200, 28.00, 22.00, 22.00, 0),
    ("FLUSH", "Saline Flush, 10 mL", "Northbridge", "NMD-SF-10", "V001", "Med-Surg Commodity", "BX", 30, 15.00, 12.00, 12.00, 0),
    ("PREP", "Alcohol Prep Pad", "Northbridge", "NMD-AP-01", "V001", "Med-Surg Commodity", "BX", 200, 7.00, 5.00, 5.00, 0),
    ("BG_GLOVE", "Nitrile Exam Glove Medium", "Bluegate", "BGM-NG-M", "V007", "Med-Surg Commodity", "BX", 100, 13.40, None, None, 0),
    ("BG_GAUZE", "4x4 Gauze Sponges", "Bluegate", "BGM-GZ-4", "V007", "Med-Surg Commodity", "BX", 200, 30.80, None, None, 0),
]

# Duplicate item-master records: same manufacturer catalog number, new item ID,
# different description. Nobody put them on contract.
DUP_ITEMS = [
    ("APX_FEM_DUP", "APX_FEM", "FEMORAL COMP CR APEX"),
    ("MJS_INS_DUP", "MJS_INS", "INSERT TIBIAL MERIDIAN"),
    ("GLOVE_DUP", "GLOVE", "GLOVE EXAM NITRILE MED"),
    ("SUTURE_DUP", "SUTURE", "SUTURE 2-0 PACK"),
]

# Riverbend providers: Orthopedic Surgery and Cardiology specialists.
ORTHO = ["PRV0002", "PRV0008", "PRV0014", "PRV0020", "PRV0026"]
EP = ["PRV0006", "PRV0012", "PRV0018", "PRV0024"]
OR_DAY = {"PRV0002": [0], "PRV0008": [1], "PRV0014": [2], "PRV0020": [3], "PRV0026": [4],
          "PRV0006": [0, 2], "PRV0012": [1], "PRV0018": [3], "PRV0024": [4]}
# Share of cases using Apex implants, before and after the 1 July conversion.
# PRV0008 never converted.
APEX_SHARE = {"PRV0002": (0.85, 0.04), "PRV0008": (0.90, 0.85), "PRV0014": (0.70, 0.04),
              "PRV0020": (0.15, 0.04), "PRV0026": (0.10, 0.04)}

PROCEDURES = [
    ("TKA", "Total Knee Arthroplasty", "Orthopedics"),
    ("THA", "Total Hip Arthroplasty", "Orthopedics"),
    ("PPM", "Pacemaker Implant, Dual Chamber", "Cardiology"),
    ("ICD", "ICD Implant", "Cardiology"),
    ("ABL", "AFib Ablation", "Cardiology"),
]

# Supplies per case, recorded in EACH (EA) regardless of how the item is bought.
BRANDED = {"FEM", "TIB", "INS", "PAT", "STEM", "SHELL", "HEAD", "LINER"}
KIT = {
    "TKA": [("FEM", 1), ("TIB", 1), ("INS", 1), ("PAT", 1), ("CEMENT", 2), ("MIXER", 1), ("DRAPE", 1),
            ("GOWN", 4), ("BLADE", 1), ("SUTURE", 3), ("STAPLER", 1), ("GLOVE", 12), ("GAUZE", 20)],
    "THA": [("STEM", 1), ("SHELL", 1), ("HEAD", 1), ("LINER", 1), ("DRAPE", 1), ("GOWN", 4),
            ("BLADE", 1), ("SUTURE", 3), ("STAPLER", 1), ("GLOVE", 12), ("GAUZE", 20)],
    "PPM": [("PM", 1), ("PM_LEAD", 2), ("INTRO", 2), ("DRAPE_CV", 1), ("GOWN", 3), ("SUTURE", 2),
            ("GLOVE", 8), ("GAUZE", 10)],
    "ICD": [("ICD", 1), ("ICD_LEAD", 1), ("INTRO", 1), ("DRAPE_CV", 1), ("GOWN", 3), ("SUTURE", 2),
            ("GLOVE", 8), ("GAUZE", 10)],
    "ABL": [("ABL", 1), ("MAP", 1), ("SHEATH", 1), ("DRAPE_CV", 1), ("GOWN", 3), ("GLOVE", 8),
            ("GAUZE", 10), ("FLUSH", 4)],
}

# Weekly replenishment to Central Supply, in purchase units (boxes or each).
WEEKLY = {"GLOVE": 60, "SYRINGE": 25, "IVKIT": 6, "GAUZE": 30, "FLUSH": 40, "PREP": 10,
          "CEMENT": 30, "MIXER": 12, "DRAPE": 16, "DRAPE_CV": 12, "GOWN": 4, "BLADE": 16,
          "SUTURE": 2, "STAPLER": 16, "INTRO": 2}

BACKORDERS = [
    # vendor, item, reported, expected release, resolved, substitute
    ("V005", "PM", date(2025, 3, 3), date(2025, 3, 17), date(2025, 3, 14), None),
    ("V001", "GLOVE", BACKORDER_START, date(2025, 8, 25), BACKORDER_END, "BG_GLOVE"),
    ("V001", "GAUZE", BACKORDER_START, date(2025, 8, 25), BACKORDER_END, "BG_GAUZE"),
    ("V002", "CEMENT", date(2025, 11, 10), date(2025, 11, 21), date(2025, 11, 24), None),
    ("V001", "FLUSH", date(2025, 11, 20), date(2025, 11, 28), date(2025, 12, 1), None),
    ("V006", "ABL", date(2025, 12, 8), date(2026, 1, 9), None, None),
    ("V004", "MJS_INS", date(2025, 12, 10), date(2025, 12, 22), None, None),
    ("V005", "ICD_LEAD", date(2025, 12, 12), date(2025, 12, 19), None, None),
]


def days(start, end):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def build():
    rng = random.Random(SEED)
    DATA.mkdir(exist_ok=True)

    # ---------------------------------------------------------------- items
    item_id, spec = {}, {}
    item_rows, contract_rows = [], []
    next_item = 100101
    for (key, desc, mfr, cat_no, vendor, category, uom, units, listp, c1, c2, implant) in ITEMS:
        item_id[key] = str(next_item)
        spec[key] = dict(vendor=vendor, uom=uom, units=units, list=listp, c1=c1, c2=c2,
                         implant=implant, category=category)
        item_rows.append((str(next_item), desc, mfr, cat_no, category, uom, units, listp, implant, "Y"))
        next_item += 1
    for dup_key, base, desc in DUP_ITEMS:
        b = ITEMS[[i[0] for i in ITEMS].index(base)]
        next_item += rng.randint(3, 40)
        item_id[dup_key] = str(next_item)
        spec[dup_key] = dict(spec[base])
        item_rows.append((str(next_item), desc, b[2], b[3], b[5], b[6], b[7], b[8], b[11], "Y"))

    contract_no = 1
    for (key, *_rest) in ITEMS:
        s = spec[key]
        if s["c1"] is None:
            continue
        if s["c2"] is None:
            periods = [(s["c1"], date(2025, 1, 1), date(2025, 6, 30))]
        elif s["c2"] == s["c1"]:
            periods = [(s["c1"], date(2025, 1, 1), date(2025, 12, 31))]
        else:
            periods = [(s["c1"], date(2025, 1, 1), date(2025, 6, 30)),
                       (s["c2"], date(2025, 7, 1), date(2025, 12, 31))]
        for price, start, end in periods:
            contract_rows.append((f"GPO-{contract_no:04d}", s["vendor"], item_id[key], price, s["uom"],
                                  start.isoformat(), end.isoformat(), "National GPO"))
            contract_no += 1

    def contract_price(key, d):
        s = spec[key]
        if key.endswith("_DUP") or s["c1"] is None:
            return None
        if d < SWITCH:
            return s["c1"]
        return s["c2"]

    # ---------------------------------------------------------------- surgeons + preference cards
    surgeon_rows = [(p, f"Provider {int(p[3:]):03d}", "Orthopedic Surgery", "Orthopedics") for p in ORTHO]
    surgeon_rows += [(p, f"Provider {int(p[3:]):03d}", "Cardiology", "Cardiology") for p in EP]

    def brand_key(component, apex):
        return ("APX_" if apex else "MJS_") + component

    card_rows, card_no = [], 1
    card_brand = {"PRV0002": ("MJS", date(2025, 6, 20)), "PRV0008": ("APX", date(2023, 11, 2)),
                  "PRV0014": ("MJS", date(2025, 6, 24)), "PRV0020": ("MJS", date(2024, 9, 12)),
                  "PRV0026": ("MJS", date(2024, 3, 5))}
    for p in ORTHO:
        brand, updated = card_brand[p]
        for proc in ("TKA", "THA"):
            for comp, qty in KIT[proc]:
                key = f"{brand}_{comp}" if comp in BRANDED else comp
                card_rows.append((f"PC{card_no:05d}", p, proc, item_id[key], qty, updated.isoformat()))
                card_no += 1
    for p in EP:
        updated = date(2025, 2, 1) + timedelta(days=rng.randint(0, 200))
        for proc in ("PPM", "ICD", "ABL"):
            for key, qty in KIT[proc]:
                card_rows.append((f"PC{card_no:05d}", p, proc, item_id[key], qty, updated.isoformat()))
                card_no += 1

    # ---------------------------------------------------------------- surgical cases + usage
    case_rows, usage_rows = [], []
    case_no, usage_no = 1, 1
    for d in days(YEAR_START, date(2025, 12, 31)):
        if d.weekday() > 4 or d in HOLIDAYS:
            continue
        for p in ORTHO + EP:
            if d.weekday() not in OR_DAY[p]:
                continue
            n = rng.choice([2, 3, 3, 4]) if p in ORTHO else rng.choice([2, 2, 3])
            for _ in range(n):
                if p in ORTHO:
                    proc = "TKA" if rng.random() < 0.6 else "THA"
                    loc = "L01"
                else:
                    r = rng.random()
                    proc = "PPM" if r < 0.40 else ("ICD" if r < 0.55 else "ABL")
                    loc = "L02"
                if d > AS_OF:
                    status = "Scheduled"
                elif rng.random() < 0.03:
                    status = "Cancelled"
                else:
                    status = "Completed"
                cid = f"SC{case_no:06d}"
                case_no += 1
                case_rows.append((cid, d.isoformat(), p, proc, loc, status))
                if status != "Completed":
                    continue
                apex = None
                if p in ORTHO:
                    share = APEX_SHARE[p][0 if d < SWITCH else 1]
                    apex = rng.random() < share
                lines = []
                for comp, qty in KIT[proc]:
                    if comp == "PAT" and rng.random() < 0.10:
                        continue
                    key = brand_key(comp, apex) if comp in BRANDED else comp
                    if key == "APX_FEM" and rng.random() < 0.20:
                        key = "APX_FEM_DUP"
                    if key == "MJS_INS" and rng.random() < 0.25:
                        key = "MJS_INS_DUP"
                    lines.append((key, qty, "N"))
                # Opened in the room, then not used (wrong size): still paid for.
                if proc == "TKA" and rng.random() < 0.05:
                    lines.append((brand_key("INS", apex), 1, "Y"))
                if proc == "THA" and rng.random() < 0.05:
                    lines.append((brand_key("LINER", apex), 1, "Y"))
                if proc == "ABL" and rng.random() < 0.03:
                    lines.append(("ABL", 1, "Y"))
                for key, qty, wasted in lines:
                    usage_rows.append((f"U{usage_no:07d}", cid, item_id[key], qty, "EA", wasted, key))
                    usage_no += 1

    # ---------------------------------------------------------------- purchase orders, receipts, invoices
    po_rows, receipt_rows, inv_rows = [], [], []
    po_no, rcpt_no = 4500001, 1
    inv_seq = {}

    def next_invoice(vendor):
        prefix = INVOICE_PREFIX[vendor]
        inv_seq[prefix] = inv_seq.get(prefix, 100200) + rng.randint(1, 9)
        return f"{prefix}-{inv_seq[prefix]}"

    invoices = []  # (invoice_number, vendor, invoice_date, [lines]) ; line = (po, po_line, key, qty, price)

    # Implants and EP catheters: bill-only, ordered after the case.
    by_case = {}
    for u in usage_rows:
        by_case.setdefault(u[1], []).append(u)
    case_date = {c[0]: date.fromisoformat(c[1]) for c in case_rows}
    for cid in sorted(by_case):
        groups = {}
        for (_uid, _cid, _iid, qty, _uom, _w, key) in by_case[cid]:
            s = spec[key]
            if not (s["implant"] or s["category"] == "EP Catheter"):
                continue
            groups.setdefault(s["vendor"], []).append((key, qty))
        for vendor in sorted(groups):
            po_date = case_date[cid] + timedelta(days=rng.randint(0, 2))
            if po_date > AS_OF:
                continue
            v = vendor
            if vendor == "V003" and rng.random() < 0.15:
                v = "V008"
            po = f"PO{po_no}"
            po_no += 1
            inv_lines = []
            for line, (key, qty) in enumerate(groups[vendor], start=1):
                price = contract_price(key, po_date)
                if price is None and key.endswith("_DUP"):
                    price = contract_price(key.replace("_DUP", ""), po_date)
                if price is None:
                    price = spec[key]["list"]
                po_rows.append((po, line, po_date.isoformat(), v, item_id[key], qty, spec[key]["uom"],
                                price, "L01" if spec[key]["category"] == "Ortho Implant" else "L02", "Bill-only"))
                receipt_rows.append((f"R{rcpt_no:07d}", po, line, po_date.isoformat(), qty))
                rcpt_no += 1
                inv_price = price
                if key == "PM" and SWITCH <= po_date <= PM_OVERBILL_END and rng.random() < 0.70:
                    inv_price = spec[key]["c1"]
                inv_lines.append((po, line, key, qty, inv_price))
            inv_date = po_date + timedelta(days=rng.randint(3, 20))
            if inv_date <= AS_OF:
                invoices.append([next_invoice(v), v, inv_date, inv_lines])

    # Weekly replenishment to Central Supply.
    receipts_by_line = {}
    for d in days(YEAR_START, AS_OF):
        if d.weekday() != 0:
            continue
        po_day = d + timedelta(days=1) if d in HOLIDAYS else d
        orders = {}
        for key in WEEKLY:
            qty = max(1, round(WEEKLY[key] * rng.uniform(0.8, 1.2)))
            k = key
            if key in ("GLOVE", "GAUZE") and BACKORDER_START <= po_day < BACKORDER_END:
                k = "BG_" + key
            elif key == "GLOVE" and rng.random() < 0.10:
                k = "GLOVE_DUP"
            elif key == "SUTURE" and rng.random() < 0.30:
                k = "SUTURE_DUP"
            orders.setdefault(spec[k]["vendor"], []).append((k, qty))
        for vendor in sorted(orders):
            v = vendor
            if vendor == "V001" and rng.random() < 0.10:
                v = "V009"
            po = f"PO{po_no}"
            po_no += 1
            inv_lines = []
            for line, (key, qty) in enumerate(orders[vendor], start=1):
                base = key.replace("_DUP", "")
                price = contract_price(base, po_day)
                if price is None:
                    price = spec[key]["list"]
                if base == "GLOVE" and SWITCH <= po_day < GLOVE_PO_FIX:
                    price = spec["GLOVE"]["c1"]       # PO system still on the old price
                po_rows.append((po, line, po_day.isoformat(), v, item_id[key], qty, spec[key]["uom"],
                                price, "L03", "Replenishment"))
                r = rng.random()
                if r < 0.01:
                    received = 0
                elif r < 0.07:
                    received = max(1, int(qty * rng.uniform(0.6, 0.9)))
                else:
                    received = qty
                rdate = po_day + timedelta(days=rng.randint(2, 5))
                if received and rdate <= AS_OF:
                    receipt_rows.append((f"R{rcpt_no:07d}", po, line, rdate.isoformat(), received))
                    rcpt_no += 1
                inv_price = price
                if base == "GLOVE" and po_day >= SWITCH:
                    inv_price = spec["GLOVE"]["c2"]   # the vendor bills the new contract price
                inv_lines.append((po, line, key, qty, inv_price))
            inv_date = po_day + timedelta(days=rng.randint(6, 20))
            if inv_date <= AS_OF:
                invoices.append([next_invoice(v), v, inv_date, inv_lines])

    # Duplicate invoices: the same bill sent again under a slightly different number.
    candidates = [inv for inv in invoices if inv[1] in ("V001", "V002", "V009") and inv[2] < date(2025, 11, 1)]
    for i, inv in enumerate(rng.sample(candidates, 12)):
        number = [inv[0] + "-1", inv[0] + " ", inv[0].lower()][i % 3]
        invoices.append([number, inv[1], inv[2] + timedelta(days=rng.randint(10, 25)), list(inv[3])])

    # Invoices with no purchase order behind them.
    for _ in range(35):
        key = rng.choice(["BLADE", "STAPLER", "DRAPE"])
        d = YEAR_START + timedelta(days=rng.randint(0, (AS_OF - YEAR_START).days))
        invoices.append([next_invoice("V002"), "V002", d, [("", None, key, rng.randint(5, 20), spec[key]["list"])]])

    invoices.sort(key=lambda inv: (inv[2], inv[0]))
    for number, vendor, inv_date, lines in invoices:
        for n, (po, po_line, key, qty, price) in enumerate(lines, start=1):
            inv_rows.append((number, n, vendor, inv_date.isoformat(), po or None, po_line, item_id[key],
                             qty, price, round(qty * price, 2)))

    # ---------------------------------------------------------------- inventory snapshots
    inv_items = {"L01": ["GLOVE", "GAUZE", "GOWN", "SUTURE", "DRAPE", "BLADE", "STAPLER", "CEMENT", "MIXER"],
                 "L04": ["GLOVE", "SYRINGE", "IVKIT", "GAUZE", "FLUSH", "PREP"]}
    par = {"GLOVE": 40, "GAUZE": 20, "GOWN": 6, "SUTURE": 4, "DRAPE": 24, "BLADE": 20, "STAPLER": 20,
           "CEMENT": 40, "MIXER": 16, "SYRINGE": 30, "IVKIT": 8, "FLUSH": 40, "PREP": 12}
    dips = {("L01", "GLOVE"): (date(2025, 10, 6), date(2025, 10, 10)),
            ("L01", "CEMENT"): (date(2025, 11, 17), date(2025, 11, 19)),
            ("L04", "SYRINGE"): (date(2025, 10, 20), date(2025, 10, 21)),
            ("L04", "FLUSH"): (date(2025, 11, 24), date(2025, 11, 28))}
    snap_rows = []
    for d in days(date(2025, 9, 15), AS_OF):
        if d == date(2025, 11, 27):
            continue  # the count job didn't run on Thanksgiving
        for loc in ("L01", "L04"):
            for key in inv_items[loc]:
                p = par[key]
                rop = max(1, round(p * 0.3))
                window = dips.get((loc, key))
                if window and window[0] <= d <= window[1]:
                    on_hand = rng.randint(0, rop)
                else:
                    on_hand = rng.randint(rop + 1, p)
                snap_rows.append((d.isoformat(), loc, item_id[key], on_hand, p, rop, spec[key]["uom"]))

    backorder_rows = []
    for n, (vendor, key, rep, exp, res, sub) in enumerate(BACKORDERS, start=1):
        backorder_rows.append((f"BO{n:03d}", vendor, item_id[key], rep.isoformat(), exp.isoformat(),
                               res.isoformat() if res else None, item_id[sub] if sub else None))

    usage_out = [u[:6] for u in usage_rows]
    return dict(
        location=(["location_id", "location_name", "department"], LOCATIONS),
        vendor=(["vendor_id", "vendor_name", "vendor_type", "tax_id"], VENDORS),
        item_master=(["item_id", "description", "manufacturer", "mfr_catalog_no", "category",
                      "purchase_uom", "units_per_uom", "list_price", "is_implant", "active_flag"], item_rows),
        contract_price=(["contract_id", "vendor_id", "item_id", "contract_price", "purchase_uom",
                         "effective_start", "effective_end", "gpo_name"], contract_rows),
        surgeon=(["surgeon_id", "surgeon_name", "specialty", "service_line"], surgeon_rows),
        procedure=(["procedure_code", "procedure_name", "service_line"], PROCEDURES),
        preference_card=(["card_line_id", "surgeon_id", "procedure_code", "item_id", "default_qty",
                          "last_updated"], card_rows),
        surgical_case=(["case_id", "case_date", "surgeon_id", "procedure_code", "location_id",
                        "case_status"], case_rows),
        case_supply_usage=(["usage_id", "case_id", "item_id", "qty_used", "uom_recorded",
                            "wasted_flag"], usage_out),
        po_line=(["po_number", "po_line", "po_date", "vendor_id", "item_id", "qty_ordered",
                  "purchase_uom", "unit_price", "ship_to_location", "po_type"], po_rows),
        receipt=(["receipt_id", "po_number", "po_line", "received_date", "qty_received"], receipt_rows),
        invoice_line=(["invoice_number", "invoice_line", "vendor_id", "invoice_date", "po_number",
                       "po_line", "item_id", "qty_invoiced", "unit_price", "line_amount"], inv_rows),
        inventory_snapshot=(["snapshot_date", "location_id", "item_id", "on_hand_qty", "par_level",
                             "reorder_point", "stock_uom"], snap_rows),
        backorder=(["backorder_id", "vendor_id", "item_id", "reported_date", "expected_release_date",
                    "resolved_date", "substitute_item_id"], backorder_rows),
    )


TYPES = {"units_per_uom": "INTEGER", "list_price": "REAL", "is_implant": "INTEGER",
         "contract_price": "REAL", "default_qty": "INTEGER", "qty_used": "INTEGER",
         "po_line": "INTEGER", "qty_ordered": "INTEGER", "unit_price": "REAL", "qty_received": "INTEGER",
         "invoice_line": "INTEGER", "qty_invoiced": "INTEGER", "line_amount": "REAL",
         "on_hand_qty": "INTEGER", "par_level": "INTEGER", "reorder_point": "INTEGER"}


def main():
    tables = build()
    if DB.exists():
        DB.unlink()
    con = sqlite3.connect(DB)
    for name, (cols, rows) in tables.items():
        with open(DATA / f"{name}.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(cols)
            w.writerows(["" if v is None else v for v in r] for r in rows)
        coldefs = ", ".join(f"{c} {TYPES.get(c, 'TEXT')}" for c in cols)
        con.execute(f"CREATE TABLE {name} ({coldefs})")
        con.executemany(f"INSERT INTO {name} VALUES ({', '.join('?' * len(cols))})", rows)
        print(f"  {name:20s} {len(rows):>7,} rows")
    con.commit()
    con.close()
    print(f"\nDatabase written to {DB.name}; CSV copies in data/")


if __name__ == "__main__":
    main()
