from aws_cdk import core as cdk
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_elasticloadbalancingv2 as lb
from aws_cdk import aws_elasticloadbalancingv2_targets as lbt
from aws_cdk import aws_certificatemanager as acm
from aws_cdk import aws_route53 as route53
from aws_cdk import aws_route53_targets as alias

# For consistency with other languages, `cdk` is the preferred import name for
# the CDK's core module.  The following line also imports it as `core` for use
# with examples from the CDK Developer's Guide, which are in the process of
# being updated to use `cdk`.  You may delete this import if you don't need it.
from aws_cdk import core


class SplunkStackStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)


        '''
        create a vpc for the splunk environment, cdk will take care of subnetting
        additionally create a sg for the splunk instance that only accepts request from the alb
        the redirect compensates for splunk trying to redirect to http on every response
        '''
        vpc = ec2.Vpc(self, 'vpc', max_azs=2)
        instance_type = ec2.InstanceType('t2.micro')
        ami = ec2.LookupMachineImage(name = 'splunk_AMI_9.1.1_2023*')
        splunk_sg = ec2.SecurityGroup(self, 'splunk_sg', vpc = vpc)
        splunk_instance = ec2.Instance(self, 'splunk', instance_type = instance_type, 
                                machine_image = ami, vpc = vpc, security_group = splunk_sg)
        alb = lb.ApplicationLoadBalancer(self, 'alb', vpc = vpc, internet_facing = True)
        splunk_sg.connections.allow_from(alb, ec2.Port.tcp(8000))
        splunk_sg.connections.allow_from(alb, ec2.Port.tcp(8088))
        alb.add_redirect()
        
        # import existing hosted zone and create certificate using dns based validation
        my_hosted_zone = route53.HostedZone.from_lookup(self, 'importedzone', domain_name='vosskuhler.com')
        certificate = acm.Certificate(self, "Certificate",
            domain_name="splunk.vosskuhler.com",
            validation=acm.CertificateValidation.from_dns(my_hosted_zone)
        )
        
        '''
        configure listeners on the alb, by default splunk uses http on 8000 and https on 8088
        ssl offloading will take care off the TLS certificate and allows us to not have to reconfigure 
        splunk to utilize https on port 8000. To check HEC health you can visit <url>:8088/services/collector/health/1.0
        '''
        listener = alb.add_listener("Listener",certificates=[lb.ListenerCertificate(certificate.certificate_arn)], port=443, open=True)
        listener.add_targets("splunk", port=8000, targets=[lbt.InstanceTarget(splunk_instance)] )
        listener_hec = alb.add_listener("Listener_hec",certificates=[lb.ListenerCertificate(certificate.certificate_arn)], port=8088, open=True, protocol=lb.ApplicationProtocol('HTTPS'))
        listener_hec.add_targets("splunk_hec", port=8088, protocol=lb.ApplicationProtocol('HTTPS'), targets=[lbt.InstanceTarget(splunk_instance)])
        listener_api = alb.add_listener("Listener_hec",certificates=[lb.ListenerCertificate(certificate.certificate_arn)], port=8089, open=True, protocol=lb.ApplicationProtocol('HTTPS'))
        listener_api.add_targets("splunk_hec", port=8089, protocol=lb.ApplicationProtocol('HTTPS'), targets=[lbt.InstanceTarget(splunk_instance)])

        
        # configure dns to forward traffic to the alb
        route53.ARecord(self, "cnamerecord",
        zone=my_hosted_zone,
        target=route53.RecordTarget.from_alias(alias.LoadBalancerTarget(alb)),
        record_name='splunk.vosskuhler.com'
        )
