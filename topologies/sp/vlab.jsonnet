local linux = {
    image: "debian-13-genericcloud-amd64.qcow2",
};

local vmx = {
    version: "24.4R1-S2.9",
    re_image: "junos-vmx-x86-64-24.4R1-S2.9.qcow2",
    fpc_image: "vFPC-20241118.img",
};

local vars = import 'vars.jsonnet';

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
            vars: vars[self.name],
        },

        vmx {
            type: "jnpr/vmx",
            id: 2,
            name: "vmx2",
            interfaces: [
                { network: "vmx1_vmx2" },
                { network: "srv2" },
            ],
            vars: vars[self.name],
        },

        linux {
            type: "linux",
            id: 3,
            name: "srv1",
            interfaces: [
                { network: "mgmt" },
                { network: "srv1" },
            ],
            vars: vars[self.name],
        },

        linux {
            type: "linux",
            id: 4,
            name: "srv2",
            interfaces: [
                { network: "mgmt" },
                { network: "srv2" },
            ],
            vars: vars[self.name],
        },
    ],
}