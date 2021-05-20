from aws_cdk import core as cdk
from aws_cdk import aws_ec2 as ec2

# For consistency with other languages, `cdk` is the preferred import name for
# the CDK's core module.  The following line also imports it as `core` for use
# with examples from the CDK Developer's Guide, which are in the process of
# being updated to use `cdk`.  You may delete this import if you don't need it.
from aws_cdk import core


class SplunkStackStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        vpc = ec2.Vpc(self, 'vpc')
        instance_type = ec2.InstanceType('t2.micro')
        ami = ec2.LookupMachineImage(name = 'splunk_AMI_8.2.0_2021*')
        # instance_type = 1
        # ami = 2
        instance = ec2.Instance(self, 'splunk', instance_type = instance_type, machine_image = ami, vpc = vpc)