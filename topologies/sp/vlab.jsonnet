local linux = {
  image: "debian-13-genericcloud-amd64.qcow2",
};

local vmx = {
  version: "24.4R1-S2.9",
  re_image: "junos-vmx-x86-64-24.4R1-S2.9.qcow2",
  fpc_image: "vFPC-20241118.img",
};

{
  networks: [
    { name: "srv1" },
    { name: "srv2" },
    { name: "vmx1_vmx2" },
  ],

  nodes: [
    vmx {
      type: "jnpr/vmx",
      id: 1,
      name: "vmx1",
      interfaces: [
        { network: "vmx1_vmx2" },
        { network: "srv1" },
      ],
      config: {
        hostname: "vmx1",
        interfaces: {
          "fxp0":     { ip: "192.168.0.1/24" },
          "ge-0/0/0": { ip: "10.0.12.1/24" },
          "ge-0/0/1": { ip: "192.168.1.254/24" },
        },
      },
    },

    vmx {
      type: "jnpr/vmx",
      id: 2,
      name: "vmx2",
      interfaces: [
        { network: "vmx1_vmx2" },
        { network: "srv2" },
      ],
      config: {
        hostname: "vmx2",
        interfaces: {
          "fxp0":     { ip: "192.168.0.2/24" },
          "ge-0/0/0": { ip: "10.0.12.2/24" },
          "ge-0/0/1": { ip: "192.168.2.254/24" },
        },
      },
    },

    linux {
      type: "linux",
      id: 3,
      name: "srv1",
      interfaces: [
        { network: "mgmt" },
        { network: "srv1" },
      ],
      config: {
        hostname: "srv1",
        interfaces: {
          "enp1s0": { ip: "192.168.0.11/24" },
          "enp2s0": { ip: "192.168.1.1/24" },
        },
      },
    },

    linux {
      type: "linux",
      id: 4,
      name: "srv2",
      interfaces: [
        { network: "mgmt" },
        { network: "srv2" },
      ],
      config: {
        hostname: "srv2",
        interfaces: {
          "enp1s0": { ip: "192.168.0.12/24" },
          "enp2s0": { ip: "192.168.2.1/24" },
        },
      },
    },
  ],
}