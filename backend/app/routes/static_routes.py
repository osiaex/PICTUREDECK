# app/routes/static_routes.py

from flask import Blueprint, send_from_directory, current_app

static_files_blueprint = Blueprint('static_files', __name__)

@static_files_blueprint.route('/outputs/<path:filename>')
def get_output_file(filename):
    """提供对生成的图片的访问"""
    output_dir = current_app.config['OUTPUTS_DIR']
    return send_from_directory(output_dir, filename)