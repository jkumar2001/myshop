## K8s Cluster

Assuming Public DNS records are in place.
Install AWS CLI, Kops and Kubectl
Setup AWS credentials (aws configure)


### Set environment

export AWS_REGION=eu-west-2
export AWS_REGION_AZS=$(aws ec2 describe-availability-zones \
--region ${AWS_REGION} \
--query 'AvailabilityZones[0:3].ZoneName' \
--output text | \
sed 's/\t/,/g')

export NAME=myshop.example.com
export KOPS_STATE_PREFIX=myshop-state-store
export KOPS_STATE_STORE=s3://${KOPS_STATE_PREFIX}
export KOPS_OIDC_STORE=s3://myshop-oidc-store/



### Create S3 bucket for state store

aws s3api create-bucket \
    --bucket ${KOPS_STATE_PREFIX} \
    --region ${AWS_REGION} \
	--create-bucket-configuration LocationConstraint=${AWS_REGION}

### Enable bucket object versioning

aws s3api put-bucket-versioning \
	--bucket ${KOPS_STATE_PREFIX}  \
	--versioning-configuration Status=Enabled

### S3 Bucket for OIDC

aws s3api create-bucket \
    --bucket ${KOPS_OIDC_STORE} \
    --region ${AWS_REGION} \
    --object-ownership BucketOwnerPreferred
aws s3api put-public-access-block \
    --bucket ${KOPS_OIDC_STORE} \
    --public-access-block-configuration BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false
aws s3api put-bucket-acl \
    --bucket ${KOPS_OIDC_STORE} \
    --acl public-read


### HA Cluster with master across 3 zones

kops create cluster \
	--name ${NAME} \
	--state ${KOPS_STATE_STORE} \
	--discovery-store=${KOPS_OIDC_STORE}/${NAME}/discovery \
	--cloud aws \
 	--control-plane-size m5.large \
 	--control-plane-count 3 \
 	--control-plane-zones ${AWS_REGION_AZS} \
	--zones ${AWS_REGION_AZS} \
	--node-size t3.large \
	--node-count 2 \
    


## Mixed instance group and lifecycle (spot and ondemand)

kops toolbox instance-selector "spot-group" \
--usage-class spot --flexible --cluster-autoscaler \
--base-instance-type "m5.large" --burst-support=false \
--deny-list '^?[1-3].*\..*' --gpus 0 \
--node-count-max 5 --node-count-min 1 \
--name ${NAME}

``` Modify following to add ondemand instance type in this instance group

    onDemandAboveBase: 50
    onDemandBase: 5

```

### Ondemand instance group

kops toolbox instance-selector "on-demand-group" \
--usage-class on-demand --cluster-autoscaler \
--base-instance-type "m5.xlarge" --burst-support=false \
--deny-list '^?[1-3].*\..*' --gpus 0 \
--node-count-max 5 --node-count-min 1 \
--name ${NAME}  

### Create Cluster

kops update cluster \
	--state=${KOPS_STATE_STORE} \
	--name=${NAME} --yes --admin 

### Install Helm

curl -sSL https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3 | bash
helm repo add stable https://charts.helm.sh/stable
helm version --short


### Install Cluster-Autoscaler

helm repo add autoscaler https://kubernetes.github.io/autoscaler
helm upgrade --install cluster-autoscaler  autoscaler/cluster-autoscaler \
  --set fullnameOverride=cluster-autoscaler \
  --set nodeSelector."kops\.k8s\.io/lifecycle"=OnDemand \
  --set cloudProvider=aws \
  --set extraArgs.scale-down-enabled=true \
  --set extraArgs.expander=random \
  --set extraArgs.balance-similar-node-groups=true \
  --set extraArgs.scale-down-unneeded-time=2m \
  --set extraArgs.scale-down-delay-after-add=2m \
  --set autoDiscovery.clusterName=${NAME} \
  --set rbac.create=true \
  --set awsRegion=${AWS_REGION} \
  --wait