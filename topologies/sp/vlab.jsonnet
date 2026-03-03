local linux = {
    type: "linux",
    image: "debian-13-genericcloud-amd64.qcow2",
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
            name: "r1",
            interfaces: interfaces[self.name],
            vars: vars[self.name],
        },

        vmx {
            id: 2,
            name: "r2",
            interfaces: interfaces[self.name],
            vars: vars[self.name],
        },

        linux {
            id: 10,
            name: "h1",
            interfaces: interfaces[self.name],
            vars: vars[self.name],
        },

        linux {
            id: 20,
            name: "h2",
            interfaces: interfaces[self.name],
            vars: vars[self.name],
        },
    ],
}