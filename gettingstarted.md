This charm is enables the use of Cilium as a CNI plugin within a Charmed Kubernetes environment. 

To use with the default 'charmed-kubernetes' charm, create an overlay file named 'cilium-cni-overlay.yaml' with the following contents: 

```
description: Overlay to add cilium instead of flannel to the standard charmed kubernetes bundle.
series: focal
applications:
  flannel:
  cilium:
    annotations:
      gui-x: '475'
      gui-y: '605'
    charm: cs:~cilium/cilium-3
  kubernetes-master:
    options: 
      allow-privileged: "true"
relations:
- - cilium:cni
  - kubernetes-master:cni
- - cilium:cni
  - kubernetes-worker:cni
```

And run: 

juju deploy charmed-kubernetes --overlay ./cilium-cni-overlay.yaml
