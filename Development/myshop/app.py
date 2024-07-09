import os
from flask import Flask, render_template, request, redirect, url_for
import csv
import io
import boto3
from botocore.exceptions import NoCredentialsError

app = Flask(__name__)

# AWS S3 configuration
S3_BUCKET = os.environ.get('AWS_S3_BUCKET')
S3_KEY = os.environ.get('AWS_ACCESS_KEY_ID')
S3_SECRET = os.environ.get('AWS_SECRET_ACCESS_KEY')
S3_LOCATION = 'http://{}.s3.amazonaws.com/'.format(S3_BUCKET)

s3 = boto3.client(
   "s3",
   aws_access_key_id=S3_KEY,
   aws_secret_access_key=S3_SECRET
)

def upload_file_to_s3(file, bucket_name=S3_BUCKET, acl="public-read"):
    try:
        s3.upload_fileobj(
            file,
            bucket_name,
            file.filename,
            ExtraArgs={
                "ACL": acl,
                "ContentType": file.content_type
            }
        )
    except NoCredentialsError:
        print("Credentials not available")
        return None
    return "{}{}".format(S3_LOCATION, file.filename)

def list_files(bucket):
    contents = []
    try:
        for item in s3.list_objects(Bucket=bucket)['Contents']:
            if item['Key'].lower().endswith('.csv'):
                contents.append(item)
    except KeyError:
        pass  # bucket may be empty
    return contents

@app.route('/', methods=['GET', 'POST'])
def upload_csv():
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)
        if file and file.filename.endswith('.csv'):
            # Upload to S3
            s3_url = upload_file_to_s3(file, S3_BUCKET)
            if s3_url is None:
                return "S3 upload failed", 400

            # Reset file pointer to beginning of file
            file.seek(0)
            
            # Parse CSV
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_data = list(csv.reader(stream))
            headers = csv_data[0]
            rows = csv_data[1:]
            return render_template('display.html', headers=headers, rows=rows, s3_url=s3_url)
    return render_template('upload.html')

@app.route('/files')
def files():
    contents = list_files(S3_BUCKET)
    return render_template('files.html', contents=contents)

if __name__ == '__main__':
    app.run(debug=True)
