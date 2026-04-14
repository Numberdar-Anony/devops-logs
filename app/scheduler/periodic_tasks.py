import asyncio
from app.celery_app import celery
from app.collectors.jenkins_collector import collect_jenkins_logs
from app.collectors.kubernetes_collector import collect_kubernetes_logs
from app.collectors.terraform_collector import collect_terraform_logs
from app.collectors.argocd_collector import collect_argocd_logs

@celery.task
def run_jenkins_collector():
    asyncio.run(collect_jenkins_logs())

@celery.task
def run_kubernetes_collector():
    asyncio.run(collect_kubernetes_logs())

@celery.task
def run_terraform_collector():
    asyncio.run(collect_terraform_logs())

@celery.task
def run_argocd_collector():
    asyncio.run(collect_argocd_logs())

@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Jenkins collector every 2 minutes
    sender.add_periodic_task(120.0, run_jenkins_collector.s(), name='jenkins-every-2-min')
    
    # Kubernetes collector every 2 minutes
    sender.add_periodic_task(120.0, run_kubernetes_collector.s(), name='k8s-every-2-min')
    
    # Terraform collector every 2 minutes
    sender.add_periodic_task(120.0, run_terraform_collector.s(), name='terraform-every-2-min')
    
    # ArgoCD collector every 2 minutes
    sender.add_periodic_task(120.0, run_argocd_collector.s(), name='argocd-every-2-min')
