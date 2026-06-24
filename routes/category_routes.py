from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from services.category_service import (
    create_category,
    get_all_categories,
    update_category,
    delete_category,
    create_subcategory,
    rename_subcategory,
    delete_subcategory,
)

category_bp = Blueprint("category", __name__, url_prefix="/categories")


def _request_json():
    return request.get_json(silent=True) or {}


# ------------------------------------------------------------------ #
#  CATEGORIES                                                          #
# ------------------------------------------------------------------ #

@category_bp.route("/", methods=["GET"])
@login_required
def list_categories():
    categories = get_all_categories(current_user.id)
    return jsonify({"categories": categories})


@category_bp.route("/", methods=["POST"])
@login_required
def create():
    data = _request_json()
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400

    new_id = create_category(
        current_user.id, name,
        data.get("icon"), data.get("color")
    )
    return jsonify({"id": new_id, "message": "Category created"}), 201


@category_bp.route("/<int:category_id>", methods=["PUT"])
@login_required
def update(category_id):
    data = _request_json()
    updated = update_category(
        category_id, current_user.id,
        data.get("name", ""),
        data.get("icon"), data.get("color")
    )
    if not updated:
        return jsonify({"error": "Not found or no changes"}), 404
    return jsonify({"message": "Category updated"})


@category_bp.route("/<int:category_id>", methods=["DELETE"])
@login_required
def delete(category_id):
    deleted = delete_category(category_id, current_user.id)
    if not deleted:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"message": "Category deleted"})


# ------------------------------------------------------------------ #
#  SUBCATEGORIES                                                       #
# ------------------------------------------------------------------ #

@category_bp.route("/<int:category_id>/subcategories", methods=["POST"])
@login_required
def add_subcategory(category_id):
    data = _request_json()
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400

    new_id = create_subcategory(category_id, name)
    return jsonify({"id": new_id, "message": "Subcategory created"}), 201


@category_bp.route("/subcategories/<int:subcategory_id>", methods=["PUT"])
@login_required
def update_sub(subcategory_id):
    data = _request_json()
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400

    updated = rename_subcategory(subcategory_id, name)
    if not updated:
        return jsonify({"error": "Not found or no changes"}), 404
    return jsonify({"message": "Subcategory updated"})


@category_bp.route("/subcategories/<int:subcategory_id>", methods=["DELETE"])
@login_required
def delete_sub(subcategory_id):
    deleted = delete_subcategory(subcategory_id)
    if not deleted:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"message": "Subcategory deleted"})
