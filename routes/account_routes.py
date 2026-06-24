from datetime import date, datetime
from decimal import Decimal

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from services.account_service import (
    create_account,
    get_account,
    get_all_accounts,
    get_total_balance,
    update_account,
    delete_account,
    add_transaction,
    update_transaction,
    delete_transaction,
    get_transaction_history_v2,
    create_transfer,
    get_spending_by_category,
    get_spending_by_account,
)
from services.dashboard_service import get_account_dashboard_summary

account_bp = Blueprint("account", __name__, url_prefix="/accounts")


def _json_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _account_dict(row):
    keys = ("id", "user_id", "name", "type", "initial_balance", "current_balance", "icon", "color", "created_at", "updated_at")
    return {key: _json_value(value) for key, value in zip(keys, row)}


def _transaction_dict(row):
    keys = ("id", "transaction_date", "amount", "type", "payment_method", "notes", "account_name", "category_name", "subcategory_name")
    return {key: _json_value(value) for key, value in zip(keys, row)}


def _request_json():
    return request.get_json(silent=True) or {}


# ------------------------------------------------------------------ #
#  ACCOUNT CRUD                                                        #
# ------------------------------------------------------------------ #

@account_bp.route("/", methods=["GET"])
@login_required
def list_accounts():
    accounts = get_all_accounts(current_user.id)
    total = get_total_balance(current_user.id)
    
    # Format the dictionary items for JSON
    formatted_accounts = []
    for acc in accounts:
        formatted = {}
        for key, value in acc.items():
            formatted[key] = _json_value(value)
        formatted_accounts.append(formatted)
        
    return jsonify({"total_balance": total, "accounts": formatted_accounts})


@account_bp.route("/", methods=["POST"])
@login_required
def create():
    data = _request_json()
    name         = data.get("name", "").strip()
    account_type = data.get("type", "bank")
    balance      = float(data.get("initial_balance", 0))
    icon         = data.get("icon")
    color        = data.get("color")

    if not name:
        return jsonify({"error": "name is required"}), 400

    new_id = create_account(current_user.id, name, account_type, balance, icon, color)
    return jsonify({"id": new_id, "message": "Account created"}), 201


@account_bp.route("/<int:account_id>", methods=["GET"])
@login_required
def get_one(account_id):
    row = get_account(account_id, current_user.id)
    if not row:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"account": _account_dict(row)})


@account_bp.route("/<int:account_id>", methods=["PUT"])
@login_required
def update(account_id):
    data = _request_json()
    updated = update_account(
        account_id, current_user.id,
        data.get("name", ""),
        data.get("type", "bank"),
        data.get("icon"),
        data.get("color"),
    )
    if not updated:
        return jsonify({"error": "Not found or no changes"}), 404
    return jsonify({"message": "Account updated"})


@account_bp.route("/<int:account_id>", methods=["DELETE"])
@login_required
def delete(account_id):
    deleted = delete_account(account_id, current_user.id)
    if not deleted:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"message": "Account deleted"})


# ------------------------------------------------------------------ #
#  TRANSACTIONS                                                        #
# ------------------------------------------------------------------ #

@account_bp.route("/transactions", methods=["GET"])
@login_required
def list_transactions():
    account_id = request.args.get("account_id", type=int)
    limit      = request.args.get("limit", 50, type=int)
    rows = get_transaction_history_v2(current_user.id, account_id, limit)
    return jsonify({"transactions": [_transaction_dict(row) for row in rows]})


@account_bp.route("/transactions", methods=["POST"])
@login_required
def create_transaction():
    data = _request_json()
    txn_type = data.get("type")

    if txn_type not in ("income", "expense"):
        return jsonify({"error": "type must be income or expense. Use /transfer for transfers."}), 400

    required = ("account_id", "amount", "payment_method", "transaction_date")
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    new_id = add_transaction(
        user_id          = current_user.id,
        account_id       = int(data["account_id"]),
        category_id      = data.get("category_id"),
        subcategory_id   = data.get("subcategory_id"),
        txn_type         = txn_type,
        amount           = float(data["amount"]),
        payment_method   = data["payment_method"],
        notes            = data.get("notes", ""),
        transaction_date = data["transaction_date"],
    )
    return jsonify({"id": new_id, "message": "Transaction created"}), 201


@account_bp.route("/transactions/<int:txn_id>", methods=["PUT"])
@login_required
def update_txn(txn_id):
    data = _request_json()
    updated = update_transaction(
        txn_id           = txn_id,
        user_id          = current_user.id,
        account_id       = int(data["account_id"]),
        category_id      = data.get("category_id"),
        subcategory_id   = data.get("subcategory_id"),
        txn_type         = data["type"],
        amount           = float(data["amount"]),
        payment_method   = data["payment_method"],
        notes            = data.get("notes", ""),
        transaction_date = data["transaction_date"],
    )
    if not updated:
        return jsonify({"error": "Transaction not found"}), 404
    return jsonify({"message": "Transaction updated"})


@account_bp.route("/transactions/<int:txn_id>", methods=["DELETE"])
@login_required
def delete_txn(txn_id):
    deleted = delete_transaction(txn_id, current_user.id)
    if not deleted:
        return jsonify({"error": "Transaction not found"}), 404
    return jsonify({"message": "Transaction deleted"})


# ------------------------------------------------------------------ #
#  TRANSFERS                                                           #
# ------------------------------------------------------------------ #

@account_bp.route("/transfer", methods=["POST"])
@login_required
def transfer():
    data = _request_json()
    required = ("from_account_id", "to_account_id", "amount", "transfer_date")
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    if data["from_account_id"] == data["to_account_id"]:
        return jsonify({"error": "Source and destination accounts must differ"}), 400

    try:
        new_id = create_transfer(
            user_id         = current_user.id,
            from_account_id = int(data["from_account_id"]),
            to_account_id   = int(data["to_account_id"]),
            amount          = float(data["amount"]),
            notes           = data.get("notes", ""),
            transfer_date   = data["transfer_date"],
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"id": new_id, "message": "Transfer completed"}), 201


# ------------------------------------------------------------------ #
#  REPORTS                                                             #
# ------------------------------------------------------------------ #

@account_bp.route("/reports/by-category", methods=["GET"])
@login_required
def report_by_category():
    account_id = request.args.get("account_id", type=int)
    start_date = request.args.get("start_date")
    end_date   = request.args.get("end_date")
    rows = get_spending_by_category(current_user.id, account_id, start_date, end_date)
    data = [{"category": r[0], "total": float(r[1])} for r in rows]
    return jsonify({"report": data})


@account_bp.route("/reports/by-account", methods=["GET"])
@login_required
def report_by_account():
    start_date = request.args.get("start_date")
    end_date   = request.args.get("end_date")
    rows = get_spending_by_account(current_user.id, start_date, end_date)
    data = [{"account": r[0], "total": float(r[1])} for r in rows]
    return jsonify({"report": data})


# ------------------------------------------------------------------ #
#  MULTI-ACCOUNT DASHBOARD SUMMARY                                     #
# ------------------------------------------------------------------ #

@account_bp.route("/dashboard", methods=["GET"])
@login_required
def account_dashboard():
    summary = get_account_dashboard_summary(current_user.id)
    summary["account_summary"] = [
        {"name": row[0], "type": row[1], "current_balance": _json_value(row[2])}
        for row in summary["account_summary"]
    ]
    summary["recent_transactions"] = [
        {
            "transaction_date": _json_value(row[0]),
            "amount": _json_value(row[1]),
            "type": row[2],
            "account_name": row[3],
            "category_name": row[4],
            "subcategory_name": row[5],
        }
        for row in summary["recent_transactions"]
    ]
    return jsonify(summary)
