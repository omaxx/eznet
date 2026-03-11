local linux = {
    type: "linux",
    image: "debian-13-genericcloud-amd64.qcow2",
    memory_mb: 1536,
};

local vmx = {
    type: "jnpr/vmx",
    version: "24.4R1-S2.9",
    re_image: "junos-vmx-x86-64-24.4R1-S2.9.qcow2",
    fpc_image: "vFPC-20241118.img",
};

local vars = import 'vars.jsonnet';
local interfaces = import 'interfaces.jsonnet';

{
    nodes: [
        vmx {
            id: 1,
            name: "p11",
            interfaces: interfaces[self.name],
            vars: vars[self.name],
        },
        vmx {
            id: 2,
            name: "p12",
            interfaces: interfaces[self.name],
            vars: vars[self.name],
        },
        vmx {
            id: 3,
            name: "p21",
            interfaces: interfaces[self.name],
            vars: vars[self.name],
        },
        vmx {
            id: 4,
            name: "p22",
            interfaces: interfaces[self.name],
            vars: vars[self.name],
        },
        vmx {
            id: 5,
            name: "r11",
            interfaces: interfaces[self.name],
            vars: vars[self.name],
        },
        vmx {
            id: 6,
            name: "r12",
            interfaces: interfaces[self.name],
            vars: vars[self.name],
        },
        vmx {
            id: 7,
            name: "r21",
            interfaces: interfaces[self.name],
            vars: vars[self.name],
        },
        vmx {
            id: 8,
            name: "r22",
            interfaces: interfaces[self.name],
            vars: vars[self.name],
        },

        linux {
            id: 11,
            name: "h11",
            interfaces: interfaces[self.name],
            vars: vars[self.name],
        },
        linux {
            id: 12,
            name: "h12",
            interfaces: interfaces[self.name],
            vars: vars[self.name],
        },
        linux {
            id: 21,
            name: "h21",
            interfaces: interfaces[self.name],
            vars: vars[self.name],
        },
        linux {
            id: 22,
            name: "h22",
            interfaces: interfaces[self.name],
            vars: vars[self.name],
        },
    ],
}