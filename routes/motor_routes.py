from flask import Blueprint, jsonify, request, current_app, session, render_template

motor_bp = Blueprint("motor", __name__)

def _require_verified():
    # Keep motors behind bogie verification
    if not session.get("bogie_verified"):
        return jsonify({"ok": False, "error": "Bogie verification required."}), 403
    return None

@motor_bp.route("/dashboard/motor")
def motor_page():
    # Page itself is gated by main before_app_request (/dashboard/*)
    return render_template("motor.html")

@motor_bp.route("/motor/status")
def motor_status():
    if _require_verified():
        return _require_verified()
    mgr = getattr(current_app, "motor", None)
    if mgr is None:
        return jsonify({"ok": False, "error": "Motor manager not initialized."}), 500
    return jsonify({"ok": True, "state": mgr.get_state()})

@motor_bp.route("/motor/move_mm", methods=["POST"])
def motor_move_mm():
    if _require_verified():
        return _require_verified()
    data = request.get_json(silent=True) or {}
    mm = data.get("mm", None)
    if mm is None:
        return jsonify({"ok": False, "error": "Missing 'mm'."}), 400
    try:
        mm_val = float(mm)
    except Exception:
        return jsonify({"ok": False, "error": "Invalid 'mm'."}), 400

    mgr = getattr(current_app, "motor", None)
    if mgr is None:
        return jsonify({"ok": False, "error": "Motor manager not initialized."}), 500

    # Send Arduino command
    mgr.send(f"MOVEMM mm={mm_val}")
    return jsonify({"ok": True})

@motor_bp.route("/motor/move_steps", methods=["POST"])
def motor_move_steps():
    if _require_verified():
        return _require_verified()
    data = request.get_json(silent=True) or {}
    steps = data.get("steps", None)
    if steps is None:
        return jsonify({"ok": False, "error": "Missing 'steps'."}), 400
    try:
        steps_val = int(steps)
    except Exception:
        return jsonify({"ok": False, "error": "Invalid 'steps'."}), 400

    mgr = getattr(current_app, "motor", None)
    if mgr is None:
        return jsonify({"ok": False, "error": "Motor manager not initialized."}), 500
    mgr.send(f"MOVE steps={steps_val}")
    return jsonify({"ok": True})

@motor_bp.route("/motor/stop", methods=["POST"])
def motor_stop():
    if _require_verified():
        return _require_verified()
    mgr = getattr(current_app, "motor", None)
    if mgr is None:
        return jsonify({"ok": False, "error": "Motor manager not initialized."}), 500
    mgr.send("s")
    return jsonify({"ok": True})

@motor_bp.route("/motor/zero", methods=["POST"])
def motor_zero():
    if _require_verified():
        return _require_verified()
    mgr = getattr(current_app, "motor", None)
    if mgr is None:
        return jsonify({"ok": False, "error": "Motor manager not initialized."}), 500
    mgr.send("ZERO")
    mgr.send("GET")
    return jsonify({"ok": True})

@motor_bp.route("/motor/get", methods=["POST"])
def motor_get():
    if _require_verified():
        return _require_verified()
    mgr = getattr(current_app, "motor", None)
    if mgr is None:
        return jsonify({"ok": False, "error": "Motor manager not initialized."}), 500
    mgr.send("GET")
    return jsonify({"ok": True})

@motor_bp.route("/motor/speed", methods=["POST"])
def motor_speed():
    if _require_verified():
        return _require_verified()
    data = request.get_json(silent=True) or {}
    us = data.get("stepPeriodUs", None)
    if us is None:
        return jsonify({"ok": False, "error": "Missing 'stepPeriodUs'."}), 400
    try:
        us_val = int(us)
    except Exception:
        return jsonify({"ok": False, "error": "Invalid 'stepPeriodUs'."}), 400
    mgr = getattr(current_app, "motor", None)
    if mgr is None:
        return jsonify({"ok": False, "error": "Motor manager not initialized."}), 500
    mgr.send(f"p{us_val}")
    return jsonify({"ok": True})
