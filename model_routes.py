"""Dashboard endpoints for LM Studio model management."""
from flask import Blueprint, jsonify, request
import model_control as control

models = Blueprint("models", __name__)


@models.get("/api/models")
def get_models():
    status = control.state()
    status["switching"] = control.switch_busy()
    try:
        return jsonify(state=status, models=control.inventory())
    except Exception as exc:
        return jsonify(state=status, models=[], error=str(exc)), 503


@models.post("/api/models/switch")
def switch_model():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Expected a JSON object"), 400
    try:
        control.start_switch(data.get("model"), data.get("context_length", 16384))
        return jsonify(status="switching"), 202
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except RuntimeError as exc:
        return jsonify(error=str(exc)), 409
    except Exception as exc:
        return jsonify(error=str(exc)), 503
