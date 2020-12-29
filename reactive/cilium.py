import json
import os
import traceback
from shlex import split
from subprocess import check_call, check_output, CalledProcessError, STDOUT

from charms.leadership import leader_get, leader_set
from charms.reactive import set_state, remove_state, when, when_any, when_not, hook
from charms.reactive import endpoint_from_flag
from charms.templating.jinja2 import render
from charmhelpers.core import hookenv
from charmhelpers.core.hookenv import config
from charmhelpers.core.hookenv import application_version_set
from charmhelpers.core.hookenv import log, resource_get, \
    unit_private_ip, is_leader, env_proxy_settings
from charmhelpers.core.host import service_running

from charms.layer import status


@hook('upgrade-charm')
def upgrade_charm():
    remove_state('cilium.cni.available')
    remove_state('cilium.version.set')
    remove_state('cilium.cni.configured')
    try:
        hookenv.log('Deleting /etc/cni/net.d/04-cilium.conf')
        os.remove('/etc/cni/net.d/04-cilium.conf')
    except FileNotFoundError as e:
        hookenv.log(e)

@when('cni.configured')
@when_not('cilium.cni.configured')
def configure_cni():
    ''' Configure Cilium CNI. '''
    status.maintenance('Configuring Cilium CNI')

    try:
        # Mount BPF filesystem
        check_output(["sudo", "mount", "bpffs", "-t", "bpf", "/sys/fs/bpf"])

        # TODO: would be better to stop the default k8s 
        # charm from setting up FAN networking in the first place
        check_output(["sudo", "fanctl", "down", "-a"]) 
    except CalledProcessError as e:
        status.waiting('Error preparing node for cilium deployment')
        log(str(e))

    os.makedirs('/etc/cni/net.d', exist_ok=True)
    cni = endpoint_from_flag('cni.configured')
    cni_config = cni.get_config()
    context = {
        'kubeconfig_path': cni_config['kubeconfig_path'],
    }
    render('04-cilium.conf', '/etc/cni/net.d/04-cilium.conf', context)
    # this call must happen on the kubernetes-master nodes for them to 
    # understand that a CNI is available.  
    cni.set_config(cidr='10.0.0.0/8', cni_conf_file='04-cilium.conf')
    set_state('cilium.cni.configured')

@when('leadership.is_leader')
@when_not('cilium.ds.deployed')
def deploy_cilium_daemonset():
    ''' Deploy the Cilium daemonset. '''
    status.maintenance('Deploying the Cilium Daemonset')
    context = {
        # 'cilium_agent_image': hookenv.config('cilium-agent-image'),
    }
    render('cilium-quick-install.yaml', '/tmp/cilium-quick-install.yaml', context)
    try:
        kubectl('apply', '-f', '/tmp/cilium-quick-install.yaml')
        set_state('cilium.ds.deployed')
        status.active('Successfully deploying the Cilium Daemonset')
    except CalledProcessError as e:
        status.waiting('Error deploying cilium daemonset')
        log(str(e))

@when('cilium.ds.deployed')
@when_not('cilium.version.set')
def set_cilium_version():
    ''' Surface the currently deployed version of cilium to Juju '''
    #TODO:  get version via kubectl exec into pod
    application_version_set("1.9.1")
    set_state('cilium.version.set')

@when('cni.is-worker')
@when('cilium.cni.configured')
@when_not('cilium.cni.running')
def set_running():
    '''Confirm that cilium-agent pods are running on worker nodes'''
    try: 
        check_output(["curl","--unix-socket","/var/run/cilium/cilium.sock","-H \"Brief:true\"","http://localhost//v1/healthz"])
        set_state('cilium.cni.running')
        status.active('Cilium CNI is running')
    except CalledProcessError as e:
        status.waiting('Unable to contact local cilium socket on k8s nodes.')
        log(str(e))


@when_any('cilium.cni.running', 'cni.is-master')
@when_not('cilium.cni.available')
def set_available():
    ''' Indicate to the CNI provider that we're ready. '''
    set_state('cilium.cni.available')
    status.active('Cilium CNI is available.')

@hook('stop')
def stop():
    set_state('cilium.stopping')

def kubectl(*args):
    cmd = ['kubectl', '--kubeconfig=/root/.kube/config'] + list(args)
    try:
        return check_output(cmd)
    except CalledProcessError as e:
        log(e.output)
        raise
