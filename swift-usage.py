#!/usr/bin/env python
import time
import argparse
import eventlet
import os,sys
import yaml
import keystoneclient.v2_0.client
import swiftclient
from swstat import report
from swstat import swstat

eventlet.patcher.monkey_patch()

def get_swift_auth(auth_url, tenant, user, password, os_options):
    """Get swift connection from args."""
    return swiftclient.client.Connection(
        auth_url,
        '%s:%s' % (tenant, user),
        password,
        auth_version=2,
        os_options=os_options).get_auth()

def main():
    endpoint_type='public'
    for line in open("/root/openrc"):
        if "OS_TENANT_NAME"  in line:
            line=line.replace('\"','').rstrip()
            line=line.split('=')
            admin_tenant=line[1]
        if "OS_USERNAME"  in line:
            line=line.replace('\"','').rstrip()
            line=line.split('=')
            admin_user=line[1]
        if "OS_PASSWORD"  in line:
            line=line.replace('\"','').rstrip()
            line=line.split('=')
            password=line[1]
        if "OS_AUTH_URL"  in line:
            line=line.replace('\"','').rstrip()
            line=line.split('=')
            auth_url=line[1]
        if "OS_REGION_NAME"  in line:
            line=line.replace('\"','').rstrip()
            line=line.split('=')
            region_name=line[1]

    keystone_cnx = keystoneclient.v2_0.client.Client(auth_url=auth_url,
                                                     username=admin_user,
                                                     password=password,
                                                     tenant_name=admin_tenant,
                                                     region_name=region_name)
    admin_token = keystone_cnx.auth_token
    os_options = {
        'endpoint_type': endpoint_type,
        'region_name': region_name,
    }
    storage_url, admin_token = get_swift_auth(auth_url,
                                                  admin_tenant,
                                                  admin_user,
                                                  password,
                                                 os_options)
    bare_storage_url = storage_url[:storage_url.find('AUTH')] + "AUTH_"

    tenant_lists = keystone_cnx.tenants.list()
    stats = []
    pile = eventlet.GreenPile(size_or_pool=10)
    U_time = int(time.time())
    for tenant in tenant_lists:
        try:
            email = keystone_cnx.users.list(tenant_id=tenant.id)[0].email
        except Exception:
            email = "None"
        try:
            pile.spawn(swstat.retrieve_account_stats, tenant,
                       bare_storage_url, os_options, admin_token, email)
        except(swiftclient.client.ClientException), x:
            print x
            continue
        for ret in pile:
            account_size=ret[0]['account_size']
            container_count=ret[0]['container_amount']
            print('projects.'+ret[0]['account_id']+'.'+region_name.title()+'.swift.container_count '+ str(container_count)+' '+str(U_time))
            print('projects.'+ret[0]['account_id']+'.'+region_name.title()+'.swift.space_usage '+ str(account_size)+' '+str(U_time))
            if account_size == 0:
                print('projects.'+ret[0]['account_id']+'.'+region_name.title()+'.swift.object_count 0 '+str(U_time))
            else:
                object_count=0
                for i in range(0, int(container_count)):
                    object_count+=ret[1][i]['object_amount']
                print('projects.'+ret[0]['account_id']+"."+region_name.title()+'.swift.object_count '+ str(object_count)+' '+str(U_time))


if __name__ == '__main__':
    main()
