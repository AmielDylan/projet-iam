"""Error handlers for the application."""
from flask import Flask, jsonify, render_template, request


def register_error_handlers(app: Flask) -> None:
    """Register error handlers with the Flask application."""

    @app.errorhandler(400)
    def bad_request(error):
        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': str(error.description) if hasattr(error, 'description') else 'Invalid request'
            }), 400
        return render_template('error.html', error_code=400, error_message='Bad Request'), 400

    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': 'Not found',
                'message': 'The requested resource was not found'
            }), 404
        return render_template('error.html', error_code=404, error_message='Page Not Found'), 404

    @app.errorhandler(500)
    def internal_error(error):
        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': 'Internal server error',
                'message': 'An unexpected error occurred'
            }), 500
        return render_template('error.html', error_code=500, error_message='Internal Server Error'), 500
