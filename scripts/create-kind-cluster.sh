#!/bin/bash

# Exit on error
set -e

# Set KUBECONFIG to the local path
export KUBECONFIG="$(pwd)/.kube/devops-logs-config"

echo "Creating kind cluster 'devops-logs-local'..."
if ! kind get clusters | grep -q "devops-logs-local"; then
  kind create cluster --name devops-logs-local --kubeconfig "$KUBECONFIG"
else
  echo "Cluster 'devops-logs-local' already exists."
fi

echo "Waiting for cluster to be ready..."
kubectl cluster-info --context kind-devops-logs-local

echo "Applying failing pod..."
kubectl apply -f k8s/failing-pod.yaml --context kind-devops-logs-local

echo "Kind cluster setup complete."
echo "KUBECONFIG is set to $KUBECONFIG"
