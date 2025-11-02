#!/bin/bash

# Simple Kubernetes Installation Script
# Usage: sudo ./install.sh master [pod-cidr] [api-server-ip]
#        sudo ./install.sh worker "join-command"

set -e

KUBE_VERSION="1.33.2-1.1"
POD_NETWORK_CIDR="${2:-10.217.0.0/16}"
APISERVER_ADVERTISE_ADDRESS="${3:-}"

if [[ $EUID -ne 0 ]]; then
    echo "Error: This script must be run as root (use sudo)"
    exit 1
fi

# Common setup for both master and worker
common_setup() {
    echo "=== Installing containerd ==="
    apt update
    apt-get install -y containerd
    
    mkdir -p /etc/containerd
    containerd config default \
    | sed 's/SystemdCgroup = false/SystemdCgroup = true/' \
    | sed 's|sandbox_image = ".*"|sandbox_image = "registry.k8s.io/pause:3.10"|' \
    | tee /etc/containerd/config.toml > /dev/null
    
    systemctl restart containerd
    systemctl enable containerd
    
    echo "=== Disabling swap ==="
    swapoff -a
    sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab
    
    echo "=== Loading kernel modules ==="
    cat <<EOF > /etc/modules-load.d/containerd.conf
overlay
EOF
    modprobe overlay
    
    echo "=== Enabling IP forwarding ==="
    sysctl -w net.ipv4.ip_forward=1
    sed -i '/^#net\.ipv4\.ip_forward=1/s/^#//' /etc/sysctl.conf
    sysctl -p
    
    echo "=== Installing Kubernetes components ==="
    apt-get install -y apt-transport-https ca-certificates curl gpg
    
    mkdir -p -m 755 /etc/apt/keyrings
    curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.33/deb/Release.key \
      | gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
    
    echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.33/deb/ /' \
      | tee /etc/apt/sources.list.d/kubernetes.list
    
    apt-get update
    apt-get install -y kubelet=$KUBE_VERSION kubeadm=$KUBE_VERSION kubectl=$KUBE_VERSION
    apt-mark hold kubelet kubeadm kubectl
    
    echo "✅ Common setup completed"
}

# Master node setup
setup_master() {
    echo "=== Setting up Kubernetes master node ==="
    
    INIT_CMD="kubeadm init --pod-network-cidr=$POD_NETWORK_CIDR --cri-socket=unix:///run/containerd/containerd.sock"
    
    if [[ -n "$APISERVER_ADVERTISE_ADDRESS" ]]; then
        INIT_CMD="$INIT_CMD --apiserver-advertise-address=$APISERVER_ADVERTISE_ADDRESS"
    fi
    
    echo "Running: $INIT_CMD"
    $INIT_CMD
    
    echo "=== Configuring kubectl ==="
    ACTUAL_USER="${SUDO_USER:-$USER}"
    ACTUAL_HOME=$(eval echo "~$ACTUAL_USER")
    
    mkdir -p "$ACTUAL_HOME/.kube"
    cp -i /etc/kubernetes/admin.conf "$ACTUAL_HOME/.kube/config"
    chown "$(id -u "$ACTUAL_USER"):$(id -g "$ACTUAL_USER")" "$ACTUAL_HOME/.kube/config"
    
    echo "=== Installing Cilium CNI ==="
    curl -L --remote-name-all https://github.com/cilium/cilium-cli/releases/latest/download/cilium-linux-amd64.tar.gz{,.sha256sum}
    sha256sum --check cilium-linux-amd64.tar.gz.sha256sum
    tar xzvfC cilium-linux-amd64.tar.gz /usr/local/bin
    rm cilium-linux-amd64.tar.gz*
    
    sudo -u "$ACTUAL_USER" cilium install
    sudo -u "$ACTUAL_USER" cilium status --wait
    
    echo ""
    echo "✅ Master node setup completed!"
    echo ""
    echo "To add worker nodes, get the join command:"
    echo "kubeadm token create --print-join-command"
    echo ""
    echo "Then run on worker nodes:"
    echo "sudo ./install.sh worker \"<join-command>\""
}

# Worker node setup
setup_worker() {
    if [[ -z "$2" ]]; then
        echo "Error: Join command required for worker setup"
        echo "Usage: sudo ./install.sh worker \"kubeadm join ...\""
        exit 1
    fi
    
    JOIN_COMMAND="$2"
    
    echo "=== Setting up Kubernetes worker node ==="
    echo "Join command: $JOIN_COMMAND"
    
    # Add CRI socket if not present
    if [[ ! "$JOIN_COMMAND" =~ --cri-socket ]]; then
        JOIN_COMMAND="$JOIN_COMMAND --cri-socket=unix:///run/containerd/containerd.sock"
    fi
    
    eval "$JOIN_COMMAND"
    
    echo ""
    echo "✅ Worker node setup completed!"
    echo "Check node status from master: kubectl get nodes"
}

# Main execution
case "${1:-}" in
    master)
        common_setup
        setup_master
        ;;
    worker)
        common_setup
        setup_worker "$@"
        ;;
    *)
        echo "Kubernetes Installation Script"
        echo ""
        echo "Usage:"
        echo "  sudo ./install.sh master [pod-cidr] [api-server-ip]"
        echo "  sudo ./install.sh worker \"join-command\""
        echo ""
        echo "Examples:"
        echo "  sudo ./install.sh master"
        echo "  sudo ./install.sh master 10.244.0.0/16"
        echo "  sudo ./install.sh master 10.244.0.0/16 10.0.1.100"
        echo "  sudo ./install.sh worker \"kubeadm join 10.0.1.100:6443 --token abc123.xyz789 --discovery-token-ca-cert-hash sha256:abcd1234...\""
        exit 1
        ;;
esac
