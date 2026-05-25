from flask import Flask, render_template, jsonify, request
import os
import socket
import datetime
import subprocess
import psutil
import json
import boto3

app = Flask(__name__)

VERSION    = os.getenv("APP_VERSION", "v1")
ENV_NAME   = os.getenv("ENV_NAME", "production")
S3_BUCKET  = os.getenv("S3_BUCKET", "devops-pipeline-deployments-archana")
START_TIME = datetime.datetime.utcnow()

def get_uptime():
    delta = datetime.datetime.utcnow() - START_TIME
    hours, rem = divmod(int(delta.total_seconds()), 3600)
    mins, secs = divmod(rem, 60)
    if hours > 0:
        return f"{hours}h {mins}m"
    elif mins > 0:
        return f"{mins}m {secs}s"
    return f"{secs}s"

def run_cmd(cmd):
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=5,
            env={**os.environ, "DOCKER_HOST": "unix:///var/run/docker.sock"}
        )
        return result.stdout.strip()
    except Exception:
        return ""

def get_docker_status():
    out = run_cmd(["docker", "ps", "--filter", "name=devops-app",
                   "--format", "{{.Status}}"])
    if out:
        return "green", "green", "RUNNING"
    return "red", "red", "STOPPED"

def get_container_info():
    cid    = socket.gethostname()
    name   = run_cmd(["docker", "inspect", cid, "--format", "{{.Name}}"])
    image  = run_cmd(["docker", "inspect", cid, "--format", "{{.Config.Image}}"])
    status = run_cmd(["docker", "inspect", cid, "--format", "{{.State.Status}}"])
    policy = run_cmd(["docker", "inspect", cid, "--format",
                      "{{.HostConfig.RestartPolicy.Name}}"])
    return {
        "name":    name.lstrip("/") if name else "devops-app",
        "image":   image if image else f"devops-app:{VERSION}",
        "status":  status if status else "running",
        "restart": policy if policy else "always",
    }

def get_jenkins_status():
    out = run_cmd(["docker", "ps", "--format", "{{.Names}}"])
    if "jenkins" in out.lower():
        return "blue", "blue", "RUNNING"
    return "red", "red", "STOPPED"

def get_system_metrics():
    cpu  = psutil.cpu_percent(interval=1)
    mem  = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    def fmt(b):
        for u in ["B", "KB", "MB", "GB"]:
            if b < 1024:
                return f"{b:.1f} {u}"
            b /= 1024
        return f"{b:.1f} TB"

    return {
        "cpu_percent":  max(1, min(int(cpu), 100)),
        "mem_percent":  min(int(mem.percent), 100),
        "disk_percent": min(int(disk.percent), 100),
        "total_ram":    fmt(mem.total),
        "used_ram":     fmt(mem.used),
        "free_ram":     fmt(mem.available),
        "cached_ram":   fmt(mem.cached),
    }

def get_deployment_history():
    try:
        s3  = boto3.client("s3", region_name="us-east-1")
        obj = s3.get_object(Bucket=S3_BUCKET, Key="deployment_history.json")
        data = json.loads(obj["Body"].read().decode())
        return data[-5:][::-1]
    except Exception:
        return []

def save_deployment_record(version, status, message):
    try:
        s3 = boto3.client("s3", region_name="us-east-1")
        try:
            obj     = s3.get_object(Bucket=S3_BUCKET, Key="deployment_history.json")
            history = json.loads(obj["Body"].read().decode())
        except Exception:
            history = []

        sc = "success" if status == "Success" else "rollback" if status == "Rolled Back" else "failed"

        history.append({
            "version":      version,
            "status":       status,
            "status_class": sc,
            "message":      message,
            "time":         datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        })
        s3.put_object(
            Bucket=S3_BUCKET,
            Key="deployment_history.json",
            Body=json.dumps(history[-20:]),
            ContentType="application/json"
        )
    except Exception as e:
        print(f"S3 save error: {e}")

@app.route("/")
def home():
    docker_dot, docker_badge, docker_lbl   = get_docker_status()
    jenkins_dot, jenkins_badge, jenkins_lbl = get_jenkins_status()
    metrics = get_system_metrics()
    cinfo   = get_container_info()
    history = get_deployment_history()

    try:
        host_ip = socket.gethostbyname(socket.gethostname())
    except Exception:
        host_ip = "unknown"

    total   = len(history)
    success = sum(1 for d in history if d.get("status") == "Success")

    return render_template("index.html",
        version=VERSION,
        environment=ENV_NAME,
        hostname=socket.gethostname(),
        host_ip=host_ip,
        current_time=datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        uptime=get_uptime(),
        total_deploys=total,
        successful_deploys=success,
        docker_status=docker_lbl,
        docker_dot=docker_dot,
        docker_badge_class=docker_badge,
        ansible_status="SUCCESS",
        ansible_dot="green",
        ansible_badge_class="green",
        jenkins_status=jenkins_lbl,
        jenkins_dot=jenkins_dot,
        jenkins_badge_class=jenkins_badge,
        health_status="HEALTHY",
        health_dot="green",
        health_badge_class="green",
        health_stage_class="done",
        health_stage_icon="✅",
        cpu_percent=metrics["cpu_percent"],
        mem_percent=metrics["mem_percent"],
        disk_percent=metrics["disk_percent"],
        total_ram=metrics["total_ram"],
        used_ram=metrics["used_ram"],
        free_ram=metrics["free_ram"],
        cached_ram=metrics["cached_ram"],
        container_name=cinfo["name"],
        container_image=cinfo["image"],
        container_status=cinfo["status"],
        container_restart=cinfo["restart"],
        deployment_history=history,
    )

@app.route("/health")
def health():
    return jsonify({
        "status":    "healthy",
        "version":   VERSION,
        "timestamp": datetime.datetime.utcnow().isoformat()
    }), 200

@app.route("/info")
def info():
    metrics = get_system_metrics()
    return jsonify({
        "app":         "DevOps Rollback Pipeline",
        "version":     VERSION,
        "environment": ENV_NAME,
        "host":        socket.gethostname(),
        "uptime":      get_uptime(),
        "cpu_percent": metrics["cpu_percent"],
        "mem_percent": metrics["mem_percent"],
    }), 200

@app.route("/record-deploy", methods=["POST"])
def record_deploy():
    data = request.get_json(silent=True) or {}
    save_deployment_record(
        data.get("version", VERSION),
        data.get("status", "Success"),
        data.get("message", "Deployed successfully")
    )
    return jsonify({"ok": True}), 200

@app.route("/container-details")
def container_details():
    try:
        cid     = socket.gethostname()
        name    = run_cmd(["docker", "inspect", cid, "--format", "{{.Name}}"])
        image   = run_cmd(["docker", "inspect", cid, "--format", "{{.Config.Image}}"])
        status  = run_cmd(["docker", "inspect", cid, "--format", "{{.State.Status}}"])
        policy  = run_cmd(["docker", "inspect", cid, "--format",
                           "{{.HostConfig.RestartPolicy.Name}}"])
        started = run_cmd(["docker", "inspect", cid, "--format", "{{.State.StartedAt}}"])
        return jsonify({
            "Name":           name.lstrip("/") if name else "devops-app",
            "Image":          image if image else f"devops-app:{VERSION}",
            "Status":         status if status else "running",
            "Started At":     started[:19].replace("T", " ") if started else "unknown",
            "Restart Policy": policy if policy else "always",
            "Port":           "0.0.0.0:5000",
            "Version":        VERSION
        })
    except Exception:
        return jsonify({
            "Name":    "devops-app",
            "Image":   f"devops-app:{VERSION}",
            "Status":  "running",
            "Port":    "0.0.0.0:5000",
            "Version": VERSION
        })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
