import functools
import os
import imghdr
from werkzeug.utils import secure_filename
from flask import (
    Blueprint, current_app, g, request, abort, jsonify, send_from_directory, json
)
from werkzeug.utils import secure_filename
from werkzeug.exceptions import HTTPException

from filesapi.db import get_db
from filesapi.visionclient import image_anlaysis


bp = Blueprint('files', __name__, url_prefix='/files')

@bp.before_app_request
def create_upload_path():
    if not os.path.exists(current_app.config['UPLOAD_PATH']):
        os.makedirs(current_app.config['UPLOAD_PATH'])


def validate_image(request):
    format = imghdr.what(None, request.data)
    if not format:
        return None
    return '.' + (format if format != 'jpeg' else 'jpg')

@bp.route("/")
def list_files():
    files = []
    existing_files = get_db().execute('SELECT * FROM files').fetchall()
    for file_entry in existing_files:
        files.append({"file" : file_entry['file_name'], "url" : file_entry['file_url'], 'tags': file_entry['tags']})
    return jsonify(files)

@bp.route("/<path:path>")
def get_file(path):
    relative_path = "../"+current_app.config['UPLOAD_PATH']
    return send_from_directory(relative_path, path)

@bp.route("/<filename>", methods=["POST"])
def post_file(filename):
    if "/" in filename:
        # Return 400 BAD REQUEST
        abort(400, "No subdirectories allowed")
    
    filename = secure_filename(filename)
    file_ext = os.path.splitext(filename)[1]
    if file_ext not in current_app.config['UPLOAD_EXTENSIONS'] or request.content_length == 0 or file_ext != validate_image(request):
        abort(400, "Invalid Image")
    with open(os.path.join(current_app.config['UPLOAD_PATH'], filename), "wb") as fp:
        fp.write(request.data)
    
    file_saved = open(os.path.join(current_app.config['UPLOAD_PATH'], filename), "rb")
    analysis_result = image_anlaysis(file_saved)
    if analysis_result.adult.is_adult_content or analysis_result.adult.is_gory_content or analysis_result.adult.is_racy_content:
        os.remove(os.path.join(current_app.config['UPLOAD_PATH'], filename))
        abort(400, "Adult content")
    url = request.url_root+"files/"+filename
    tags = ",".join(map(str,analysis_result.description.tags))
    description = analysis_result.description.captions[0].text
    if (len(analysis_result.description.captions) == 0):
        description = 'No description was generated'
    else:
        for caption in analysis_result.description.captions:
            description = description + " '{}'\n(Confidence: {:.2f}%)".format(caption.text, caption.confidence * 100)

    existing_file = get_db().execute('SELECT * FROM files WHERE file_name = ?', (filename,)).fetchone()
    if existing_file is None:
        db = get_db()
        query = 'INSERT INTO files (file_name, file_url, tags) VALUES (?, ?, ?)'
        db.execute(query,(filename, url, tags))
        db.commit()
    else:
        db = get_db()
        query = 'UPDATE files SET file_name = ?, file_url = ?, tags = ? WHERE id = ?'
        db.execute(query,(filename, url, tags, existing_file['id']))
        db.commit()
    # Return 201 CREATED
    new_file = {"file" : filename, "url" : url, "tags": tags }
    return jsonify(new_file), 201


@bp.errorhandler(413)
def too_large(error):
    message = {
        "name":"Request Entity Too Large",
        "code" : 413,
        "description" : "File is too large."}
    return jsonify(message), 413
@bp.errorhandler(404)
def not_found(error):
    message = {
        "name":"Not Found",
        "code" : 404,
        "description" : "The requested URL was not found on the server. If you entered the URL manually please check your spelling and tryagain."}
    return jsonify(message), 404
@bp.errorhandler(405)
def not_allowed(error):
    message = {
        "name":"Method Not Allowed",
        "code" : 405,
        "description" : "The method is not allowed for the requested URL."}
    return jsonify(message), 405
@bp.errorhandler(400)
def bad_request(error):
    response = error.get_response()
    response.data = json.dumps({
        "code": error.code,
        "name": error.name,
        "description": error.description,
    })
    response.content_type = "application/json"
    return response
