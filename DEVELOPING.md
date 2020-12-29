# Developing cilium-charm

## Installing build dependencies

To install build dependencies:

```
sudo snap install charm --classic
sudo apt install docker.io
sudo usermod -aG docker $USER
```

After running these commands, terminate your shell session and start a new one
to pick up the modified user groups.

## Building the charm

To build the charm:
```
charm build
```

By default, this will build the charm and place it in
`/tmp/charm-builds/cilium`.

## Testing

You can test a locally built canal charm by deploying it with Charmed
Kubernetes.

Create a file named `local-cilium-cni-overlay.yaml` that contains the following (with paths
adjusted to fit your environment):
```
applications:
  flannel:
  cilium:
    charm: /tmp/charm-builds/cilium
  kubernetes-master:
    options: 
      allow-privileged: "true"
relations:
- - cilium:cni
  - kubernetes-master:cni
- - cilium:cni
  - kubernetes-worker:cni
```

Then deploy Charmed Kubernetes with your locally built cilium charm:

```
juju deploy charmed-kubernetes --overlay local-cilium-cni-overlay.yaml
```

Deploy the following set of pods and confirm that all pods become 1/1 ready status: 

kubectl  apply -f https://raw.githubusercontent.com/cilium/cilium/master/examples/kubernetes/connectivity-check/connectivity-check.yaml


## Helpful links

* [Getting Started with charm development](https://jaas.ai/docs/getting-started-with-charm-development)
* [Charm tools documentation](https://jaas.ai/docs/charm-tools)
