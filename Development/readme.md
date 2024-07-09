## python flask app for csv file upload/parse and store on S3

### S3 bucket create and glacier lifecycle

```
cat <<EOF > lifecycle.json
{
    "Rules": [
        {
            "Status": "Enabled",
            "Prefix": "",
            "NoncurrentVersionTransitions": [
                {
                    "NoncurrentDays": 15,
                    "StorageClass": "GLACIER"
                }
            ],
            "ID": "Move old csv to Glacier"
        }
    ]
}
EOF
```

### AWS CLI

```
aws s3api create-bucket --bucket myshop-csv-bucket --region eu-west-1
aws s3api put-bucket-lifecycle-configuration --bucket myshop-csv-bucket --lifecycle-configuration  file://lifecycle.json
```
