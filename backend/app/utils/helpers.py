# app/utils/helpers.py
from flask import jsonify

def api_response(code, message, data=None):
    """
    统一的API响应格式化函数
    """
    response = {
        'code': code,
        'message': message
    }
    if data is not None:
        response['data'] = data
    # 所有业务逻辑都在JSON Body里体现，所以HTTP状态码统一为200
    return jsonify(response), 200