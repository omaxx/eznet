local vqfx = {
  version: "19.4",
  re_image: "vqfx-19.4R1.10-re-qemu.qcow2",
  fpc_image: "vqfx-19.4R1-2019010209-pfe-qemu.qcow",
};

{
  networks: [
    { name: "qfx1_qfx2" },
  ],

  nodes: [
    vqfx {
      type: "jnpr/vqfx",
      id: 1,
      name: "qfx1",
      interfaces: [
        { network: "qfx1_qfx2" },
      ],
      config: {
        hostname: "qfx1",
        interfaces: {
          "fxp0":     { ip: "192.168.0.1/24" },
          "ge-0/0/0": { ip: "10.0.12.1/24" },
        },
      },
    },

    vqfx {
      type: "jnpr/vqfx",
      id: 2,
      name: "qfx2",
      interfaces: [
        { network: "qfx1_qfx2" },
      ],
      config: {
        hostname: "qfx2",
        interfaces: {
          "fxp0":     { ip: "192.168.0.2/24" },
          "ge-0/0/0": { ip: "10.0.12.2/24" },
        },
      },
    },
  ],
}