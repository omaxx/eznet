{
    p11: [
        { network: "p11_p21" },
        { network: "p11_p22" },
        { network: "p11_r11" },
        { network: "p11_r12" },
        { network: "p11_p12" },
    ],
    p12: [
        { network: "p12_p22" },
        { network: "p12_p21" },
        { network: "p12_r11" },
        { network: "p12_r12" },
        { network: "p11_p12" },
    ],
    p21: [
        { network: "p11_p21" },
        { network: "p12_p21" },
        { network: "p21_r21" },
        { network: "p21_r22" },
        { network: "p21_p22" },
    ],
    p22: [
        { network: "p12_p22" },
        { network: "p11_p22" },
        { network: "p22_r21" },
        { network: "p22_r22" },
        { network: "p21_p22" },
    ],
    r11: [
        { network: "p11_r11" },
        { network: "p12_r11" },
        { network: "r11_r12" },
        { network: "r11_r21" },
        { network: "h11" },
    ],
    r12: [
        { network: "p11_r12" },
        { network: "p12_r12" },
        { network: "r11_r12" },
        { network: "r12_r22" },
        { network: "h12" },
    ],
    r21: [
        { network: "p21_r21" },
        { network: "p22_r21" },
        { network: "r21_r22" },
        { network: "r11_r21" },
        { network: "h21" },
    ],
    r22: [
        { network: "p21_r22" },
        { network: "p22_r22" },
        { network: "r21_r22" },
        { network: "r12_r22" },
        { network: "h22" },
    ],
    h11: [
        { bridge: "mgmt" },
        { network: "h11" },
    ],
    h12: [
        { bridge: "mgmt" },
        { network: "h12" },
    ],
    h21: [
        { bridge: "mgmt" },
        { network: "h21" },
    ],
    h22: [
        { bridge: "mgmt" },
        { network: "h22" },
    ],
}