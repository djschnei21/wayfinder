from flask import Flask, render_template, redirect, abort, request, jsonify, session, send_from_directory
from functools import wraps
import secrets
import requests
from collections import defaultdict

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)  # Generate secure secret key for sessions

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'nomad_url' not in session:
            return redirect('/')
        return f(*args, **kwargs)
    return decorated

def get_service_health(nomad_url, alloc_id, service_name, token=None):
    """Get health status for a specific service by checking its allocation"""
    try:
        headers = {'X-Nomad-Token': token} if token else {}
        checks_url = f"{nomad_url.rstrip('/')}/v1/allocation/{alloc_id}/checks"
        r = requests.get(checks_url, headers=headers)
        r.raise_for_status()
        checks = r.json()
        
        # Format check details for tooltip, filtering for this specific service
        check_details = []
        is_healthy = True
        
        for check_id, check in checks.items():
            # Only include checks for this specific service
            if check.get('Service') == service_name:
                status = check.get('Status', 'unknown')
                is_healthy = is_healthy and status == 'success'
                check_details.append({
                    'name': check.get('Check', 'Unknown Check'),
                    'status': status,
                    'output': check.get('Output', ''),
                    'timestamp': check.get('Timestamp', 0)
                })
        
        return {
            'healthy': is_healthy if check_details else True,  # Consider healthy if no checks
            'checks': check_details
        }
    except Exception as e:
        print(f"Error checking service health for allocation {alloc_id}: {e}")
        return {'healthy': False, 'checks': []}

def get_nomad_services(nomad_url, token=None):
    """Get services from Nomad"""
    try:
        headers = {'X-Nomad-Token': token} if token else {}
        
        # Get list of all services
        services_url = f"{nomad_url.rstrip('/')}/v1/services"
        print(f"\nDiscovering Nomad Services:")
        print(f"└─ GET {services_url}")
        r = requests.get(f"{services_url}?namespace=*", headers=headers)
        print(f"   ├─ Status: {r.status_code}")
        r.raise_for_status()
        services_list = r.json()
        
        services = []
        for svc in services_list:
            namespace = svc.get('Namespace', 'default')
            for service in svc.get('Services', []):
                service_name = service.get('ServiceName')
                
                # Get details for each service
                details_url = f"{nomad_url.rstrip('/')}/v1/service/{service_name}"
                print(f"   ├─ Service '{service_name}':")
                print(f"   │  └─ GET {details_url}")
                r = requests.get(details_url, params={'namespace': namespace}, headers=headers)
                print(f"   │     └─ Status: {r.status_code}")
                r.raise_for_status()
                
                instances = r.json()
                print(f"   │        └─ Instances found: {len(instances)}")
                
                for instance in instances:
                    alloc_id = instance.get('AllocID')
                    if not alloc_id:
                        print(f"   │           └─ Warning: No allocation ID")
                        continue
                    
                    # Rest of instance processing...
                    health_info = get_service_health(nomad_url, alloc_id, service_name, token)
                    services.append({
                        'name': service_name,
                        'address': instance.get('Address', 'localhost'),
                        'port': instance.get('Port'),
                        'job': instance.get('JobID', 'Unknown Job'),
                        'namespace': instance.get('Namespace', 'default'),
                        'healthy': health_info['healthy'],
                        'health_checks': health_info['checks']
                    })
        
        print(f"   └─ Total services processed: {len(services)}")
        return services
    except Exception as e:
        print(f"   └─ Error: {str(e)}")
        if hasattr(e, 'response'):
            print(f"      └─ Response: {e.response.status_code} - {e.response.text}")
        return []

def get_consul_services(consul_url, token=None):
    """Get services from Consul catalog"""
    try:
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        if token:
            headers['X-Consul-Token'] = token
        
        # Get service list
        services_url = f"{consul_url}/v1/catalog/services"
        print(f"\nDiscovering Consul Services:")
        print(f"└─ GET {services_url}")
        r = requests.get(services_url, headers=headers)
        print(f"   ├─ Status: {r.status_code}")
        r.raise_for_status()
        services_list = r.json()
        
        services = []
        for service_name, tags in services_list.items():
            print(f"   ├─ Service '{service_name}':")
            
            # Get service details and health checks
            details_url = f"{consul_url}/v1/catalog/service/{service_name}"
            checks_url = f"{consul_url}/v1/health/checks/{service_name}"
            
            print(f"   │  ├─ GET {details_url}")
            r = requests.get(details_url, headers=headers)
            print(f"   │  │  └─ Status: {r.status_code}")
            r.raise_for_status()
            instances = r.json()
            
            print(f"   │  ├─ GET {checks_url}")
            r_checks = requests.get(checks_url, headers=headers)
            print(f"   │  │  └─ Status: {r_checks.status_code}")
            r_checks.raise_for_status()
            service_checks = r_checks.json()
            
            print(f"   │  └─ Instances found: {len(instances)}")
            
            for instance in instances:
                service_addr = instance.get('ServiceAddress')
                node_addr = instance.get('Address')
                port = instance.get('ServicePort')
                namespace = instance.get('Namespace', 'default')
                service_id = instance.get('ServiceID')
                
                if not service_addr and not node_addr:
                    print(f"   │     └─ Warning: No address found")
                    continue

                # Filter checks for this specific service instance
                instance_checks = [
                    check for check in service_checks
                    if check.get('ServiceID') == service_id
                ]
                
                services.append({
                    'name': service_name,
                    'address': service_addr or node_addr,
                    'port': port,
                    'job': "Consul Service",
                    'namespace': f"consul/{namespace}",
                    'healthy': all(check.get('Status') == 'passing' 
                                 for check in instance_checks),
                    'health_checks': [{
                        'name': check.get('Name', 'Unknown Check'),
                        'status': check.get('Status', 'unknown'),
                        'output': check.get('Output', ''),
                        'timestamp': check.get('LastUpdateTime', 0)
                    } for check in instance_checks]
                })
        
        print(f"   └─ Total services processed: {len(services)}")
        return services
    except Exception as e:
        print(f"   └─ Error: {str(e)}")
        if hasattr(e, 'response'):
            print(f"      └─ Response: {e.response.status_code} - {e.response.text}")
        return []

def get_service_registration(nomad_url, namespace, service_name, token=None):
    try:
        headers = {'X-Nomad-Token': token} if token else {}
        # Ensure URL ends with /v1/service
        api_url = nomad_url.rstrip('/') + '/v1/service/' + service_name
        print(f"Fetching service registration from: {api_url}")  # Debug log
        params = {'namespace': namespace}
        r = requests.get(api_url, params=params, headers=headers)
        r.raise_for_status()
        regs = r.json()
        return regs[0] if regs else None
    except Exception as e:
        print(f"Error fetching registration for {service_name} in {namespace}: {e}")
        return None

@app.route("/")
def index():
    return render_template("setup.html")

@app.route("/dashboard")
@require_auth
def dashboard():
    """Main navigation page with dynamic service loading"""
    return render_template("index.html")  # No need to pass services, will be loaded via API

@app.route("/api/config", methods=['POST'])
def save_config():
    # Normalize URLs by ensuring they don't end with a slash
    nomad_url = request.form.get('nomad_url', '').strip().rstrip('/')
    consul_url = request.form.get('consul_url', '').strip().rstrip('/')
    
    if not nomad_url:
        return jsonify({"error": "Nomad URL is required"}), 400
        
    session['nomad_url'] = nomad_url
    
    # Handle Consul URL - remove from session if empty
    if consul_url:
        session['consul_url'] = consul_url
    else:
        session.pop('consul_url', None)  # Remove if exists
        session.pop('consul_token', None)  # Also remove consul token
    
    # Handle tokens
    nomad_token = request.form.get('nomad_token', '').strip()
    consul_token = request.form.get('consul_token', '').strip()
    
    if nomad_token:
        session['nomad_token'] = nomad_token
    if consul_token and consul_url:  # Only save consul token if we have a consul URL
        session['consul_token'] = consul_token
        
    return jsonify({"status": "ok"})

@app.route("/api/config", methods=['GET'])
def get_config():
    return jsonify({
        "nomad_url": session.get('nomad_url', ''),
        "consul_url": session.get('consul_url', ''),
        "has_nomad_token": bool(session.get('nomad_token')),
        "has_consul_token": bool(session.get('consul_token'))
    })

@app.route("/api/services")
@require_auth
def get_services():
    nomad_url = session.get('nomad_url')
    consul_url = session.get('consul_url')
    nomad_token = session.get('nomad_token')
    consul_token = session.get('consul_token')
    
    if not nomad_url:
        return jsonify({"error": "Please configure Wayfinder with a valid Nomad URL"}), 400

    # Group services by namespace
    namespace_services = defaultdict(list)
    
    # Get and process Nomad services
    for svc in get_nomad_services(nomad_url, nomad_token):
        if not svc.get('name'):
            continue
            
        namespace = svc.get('namespace', 'default')
        address = svc.get('address', 'localhost')
        port = svc.get('port')
        full_url = f"{address}:{port}" if port else None
        
        namespace_services[namespace].append({
            "id": f"{namespace}-{svc['name']}",
            "name": svc['name'],
            "navigate_url": f"/service/{namespace}/{svc['name']}",
            "full_service_url": full_url,
            "job": svc.get('job', 'Unknown Job'),
            "healthy": svc.get('healthy', False),
            "health_checks": svc.get('health_checks', [])
        })
    
    # Sort Nomad services
    sorted_namespaces = {}
    for namespace in sorted(namespace_services.keys()):
        services_by_job = defaultdict(list)
        for service in namespace_services[namespace]:
            services_by_job[service['job']].append(service)
        
        sorted_jobs = {}
        for job in sorted(services_by_job.keys()):
            sorted_jobs[job] = sorted(services_by_job[job], key=lambda x: x['name'])
            
        sorted_namespaces[namespace] = []
        for job in sorted(sorted_jobs.keys()):
            sorted_namespaces[namespace].extend(sorted_jobs[job])
    
    # Handle Consul services
    if consul_url:
        for svc in get_consul_services(consul_url, consul_token):
            if not svc.get('name'):
                continue
                
            address = svc.get('address', 'localhost')
            port = svc.get('port')
            full_url = f"{address}:{port}" if port else None
            namespace = svc.get('namespace', 'consul/default')
            
            namespace_services[namespace].append({
                "id": f"consul-{svc['name']}",
                "name": svc['name'],
                "navigate_url": f"/service/{namespace}/{svc['name']}",
                "full_service_url": full_url,
                "job": svc.get('job', 'Consul Service'),
                "healthy": svc.get('healthy', False),
                "health_checks": svc.get('health_checks', [])
            })
    
    # Sort all namespaces together (both Nomad and Consul)
    sorted_namespaces = {}
    for namespace in sorted(namespace_services.keys()):
        services_by_job = defaultdict(list)
        for service in namespace_services[namespace]:
            services_by_job[service['job']].append(service)
        
        sorted_jobs = {}
        for job in sorted(services_by_job.keys()):
            sorted_jobs[job] = sorted(services_by_job[job], key=lambda x: x['name'])
            
        sorted_namespaces[namespace] = []
        for job in sorted(sorted_jobs.keys()):
            sorted_namespaces[namespace].extend(sorted_jobs[job])

    return jsonify(sorted_namespaces)

@app.route("/service/<namespace>/<service_name>")
@require_auth
def service_redirect(namespace, service_name):
    nomad_url = session.get('nomad_url')
    consul_url = session.get('consul_url')
    nomad_token = session.get('nomad_token')
    consul_token = session.get('consul_token')
    
    # Try Nomad first
    if nomad_url:
        reg = get_service_registration(nomad_url, namespace, service_name, nomad_token)
        if reg:
            address = reg.get("Address", "localhost")
            port = reg.get("Port")
            if port:
                return redirect(f"http://{address}:{port}")
    
    # Try Consul if available
    if consul_url:
        try:
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            if consul_token:
                headers['X-Consul-Token'] = consul_token
                
            r = requests.get(f"{consul_url}/v1/health/service/{service_name}", headers=headers)
            r.raise_for_status()
            instances = r.json()
            if instances:
                service = instances[0].get('Service', {})
                address = service.get('Address', 'localhost')
                port = service.get('Port')
                if port:
                    return redirect(f"http://{address}:{port}")
        except Exception as e:
            print(f"Error looking up service in Consul: {e}")
    
    return abort(404, description=f"Service '{service_name}' not found in namespace '{namespace}'.")

@app.route('/static/logos/<path:filename>')
def serve_logo(filename):
    return send_from_directory('logos', filename)

if __name__ == "__main__":
    app.run(debug=True)